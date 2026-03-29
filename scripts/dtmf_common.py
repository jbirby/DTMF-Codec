"""
DTMF (Dual-Tone Multi-Frequency) Signaling Codec

Shared module for DTMF encoding and decoding.
Implements ITU-T Q.23/Q.24 standard telephony signaling.
"""

import numpy as np
import wave
import struct

# ITU-T Q.23/Q.24 DTMF Frequency Specifications
# Row frequencies (low group)
ROW_FREQUENCIES = [697, 770, 852, 941]

# Column frequencies (high group)
COL_FREQUENCIES = [1209, 1336, 1477, 1633]

# DTMF Keypad Layout: rows x columns
# Standard 4x4 grid
DTMF_KEYPAD = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D'],
]

# Reverse mapping: digit -> (row_freq, col_freq)
DIGIT_TO_FREQS = {}
for row_idx, row in enumerate(DTMF_KEYPAD):
    for col_idx, digit in enumerate(row):
        DIGIT_TO_FREQS[digit] = (ROW_FREQUENCIES[row_idx], COL_FREQUENCIES[col_idx])

# Constants
SAMPLE_RATE = 44100  # Hz (telephony also uses 8000 Hz, but 44.1kHz is more common for audio)
DEFAULT_TONE_DURATION = 0.1  # seconds (ITU-T minimum is 65ms, we use 100ms)
DEFAULT_PAUSE_DURATION = 0.1  # seconds (ITU-T minimum is 65ms, we use 100ms)

# Tone detection parameters
ENERGY_THRESHOLD = 0.02  # Relative energy threshold for tone detection
TWIST_RATIO = 1.4  # Maximum acceptable ratio between high and low group energy


def generate_dtmf_tone(digit, tone_duration=DEFAULT_TONE_DURATION,
                       pause_duration=DEFAULT_PAUSE_DURATION,
                       sample_rate=SAMPLE_RATE):
    """
    Generate audio samples for a single DTMF digit.

    Args:
        digit (str): Single digit ('0'-'9', '*', '#', 'A'-'D')
        tone_duration (float): Duration of tone in seconds
        pause_duration (float): Duration of silence after tone in seconds
        sample_rate (int): Sample rate in Hz

    Returns:
        np.ndarray: Audio samples (normalized to [-1, 1])
    """
    if digit not in DIGIT_TO_FREQS:
        raise ValueError(f"Invalid DTMF digit: {digit}")

    low_freq, high_freq = DIGIT_TO_FREQS[digit]

    # Generate tone samples
    tone_samples = int(tone_duration * sample_rate)
    t = np.arange(tone_samples) / sample_rate

    # Generate both sine waves at equal amplitude
    low_sine = np.sin(2 * np.pi * low_freq * t)
    high_sine = np.sin(2 * np.pi * high_freq * t)

    # Combine signals
    combined = low_sine + high_sine

    # Normalize to prevent clipping
    max_val = np.max(np.abs(combined))
    if max_val > 0:
        combined = combined / (max_val * 1.1)  # Leave slight headroom

    # Add pause (silence)
    pause_samples = int(pause_duration * sample_rate)
    pause = np.zeros(pause_samples)

    # Concatenate tone and pause
    signal = np.concatenate([combined, pause])

    return signal.astype(np.float32)


def encode_dtmf_string(digit_string, tone_duration=DEFAULT_TONE_DURATION,
                       pause_duration=DEFAULT_PAUSE_DURATION,
                       sample_rate=SAMPLE_RATE):
    """
    Encode a string of DTMF digits to audio samples.

    Args:
        digit_string (str): String of digits to encode
        tone_duration (float): Duration of each tone in seconds
        pause_duration (float): Duration of silence between tones in seconds
        sample_rate (int): Sample rate in Hz

    Returns:
        np.ndarray: Concatenated audio samples for all digits
    """
    all_samples = []

    for digit in digit_string:
        if digit == ' ':
            # Space = extra pause
            pause_samples = int(pause_duration * sample_rate)
            all_samples.append(np.zeros(pause_samples, dtype=np.float32))
        else:
            samples = generate_dtmf_tone(digit, tone_duration, pause_duration, sample_rate)
            all_samples.append(samples)

    return np.concatenate(all_samples)


def write_wav(filename, samples, sample_rate=SAMPLE_RATE):
    """
    Write audio samples to a 16-bit mono WAV file.

    Args:
        filename (str): Output WAV filename
        samples (np.ndarray): Audio samples (float32, normalized to [-1, 1])
        sample_rate (int): Sample rate in Hz
    """
    # Convert float32 to int16
    int_samples = np.clip(samples * 32767, -32768, 32767).astype(np.int16)

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int_samples.tobytes())


def read_wav(filename):
    """
    Read a WAV file and return samples and sample rate.

    Args:
        filename (str): Input WAV filename

    Returns:
        tuple: (samples as float32 [-1, 1], sample_rate in Hz)
    """
    with wave.open(filename, 'rb') as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()

        audio_data = wav_file.readframes(n_frames)

        # Convert bytes to numpy array
        if sample_width == 2:
            samples = np.frombuffer(audio_data, dtype=np.int16)
        elif sample_width == 4:
            samples = np.frombuffer(audio_data, dtype=np.int32)
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

        # Normalize to [-1, 1]
        samples = samples.astype(np.float32) / (2 ** (8 * sample_width - 1))

        # Convert to mono if stereo
        if n_channels == 2:
            samples = samples.reshape(-1, 2).mean(axis=1)

        return samples, sample_rate


def goertzel_energy(samples, frequency, sample_rate):
    """
    Compute energy of a specific frequency using the Goertzel algorithm.

    The Goertzel algorithm is more efficient than FFT for detecting specific
    frequencies and is ideal for DTMF decoding.

    Args:
        samples (np.ndarray): Input audio samples
        frequency (float): Target frequency in Hz
        sample_rate (int): Sample rate in Hz

    Returns:
        float: Energy (power) at the target frequency
    """
    n = len(samples)
    if n == 0:
        return 0.0

    # Normalized frequency
    k = frequency / sample_rate
    w = 2 * np.pi * k

    # Goertzel coefficients
    cos_w = np.cos(w)
    coeff = 2 * cos_w

    # Initialize state variables
    s_prev = 0.0
    s_prev2 = 0.0

    # Run the filter
    for sample in samples:
        s = sample + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s

    # Compute power
    real = s_prev - s_prev2 * cos_w
    imag = s_prev2 * np.sin(w)
    power = real * real + imag * imag

    # Normalize by window size
    energy = power / (n * n)

    return energy


def detect_dtmf_frequencies(samples, sample_rate=SAMPLE_RATE):
    """
    Detect which DTMF frequencies are present in a signal segment.

    Uses the Goertzel algorithm to compute energy at all 8 DTMF frequencies.

    Args:
        samples (np.ndarray): Audio segment
        sample_rate (int): Sample rate in Hz

    Returns:
        tuple: (row_frequency, col_frequency) or (None, None) if no valid DTMF detected
    """
    if len(samples) == 0:
        return None, None

    # Compute energy at all DTMF frequencies
    all_frequencies = ROW_FREQUENCIES + COL_FREQUENCIES
    energies = [goertzel_energy(samples, freq, sample_rate) for freq in all_frequencies]

    # Find maximum energy in each group
    row_energies = energies[:4]
    col_energies = energies[4:]

    max_row_energy = max(row_energies)
    max_col_energy = max(col_energies)

    # Check if energy is above threshold (more lenient)
    max_overall_energy = max(max_row_energy, max_col_energy)
    if max_overall_energy < ENERGY_THRESHOLD * 0.5:  # More lenient threshold
        return None, None

    # Check twist (energy ratio between high and low groups)
    # Allow up to 2:1 ratio instead of 1.4:1
    if max_row_energy > 0 and max_col_energy > 0:
        ratio = max(max_row_energy, max_col_energy) / min(max_row_energy, max_col_energy)
        if ratio > 2.0:  # More lenient
            return None, None

    # Verify we have a clear second-place frequency
    # (to avoid false positives on noise)
    row_sorted = sorted(enumerate(row_energies), key=lambda x: x[1], reverse=True)
    col_sorted = sorted(enumerate(col_energies), key=lambda x: x[1], reverse=True)

    if len(row_sorted) > 1 and len(col_sorted) > 1:
        # Check that the best frequency is significantly stronger than second-best
        if row_sorted[0][1] > 0:
            row_ratio = row_sorted[0][1] / (row_sorted[1][1] + 1e-10)
            if row_ratio < 1.5:  # Best should be at least 1.5x stronger than second
                return None, None

        if col_sorted[0][1] > 0:
            col_ratio = col_sorted[0][1] / (col_sorted[1][1] + 1e-10)
            if col_ratio < 1.5:
                return None, None

    # Identify strongest frequencies
    row_idx = np.argmax(row_energies)
    col_idx = np.argmax(col_energies)

    row_freq = ROW_FREQUENCIES[row_idx]
    col_freq = COL_FREQUENCIES[col_idx]

    return row_freq, col_freq


def freqs_to_digit(row_freq, col_freq):
    """
    Convert row and column frequencies to DTMF digit.

    Args:
        row_freq (float): Row frequency in Hz
        col_freq (float): Column frequency in Hz

    Returns:
        str: DTMF digit ('0'-'9', '*', '#', 'A'-'D')
    """
    # Find closest matching frequencies (with tolerance)
    freq_tolerance = 20  # Hz

    row_idx = None
    col_idx = None

    for i, rf in enumerate(ROW_FREQUENCIES):
        if abs(row_freq - rf) < freq_tolerance:
            row_idx = i
            break

    for i, cf in enumerate(COL_FREQUENCIES):
        if abs(col_freq - cf) < freq_tolerance:
            col_idx = i
            break

    if row_idx is None or col_idx is None:
        return None

    return DTMF_KEYPAD[row_idx][col_idx]


def segment_dtmf_tones(samples, sample_rate=SAMPLE_RATE,
                       tone_duration=DEFAULT_TONE_DURATION,
                       pause_duration=DEFAULT_PAUSE_DURATION):
    """
    Segment audio into individual DTMF tone chunks.

    Detects tone onset/offset using energy threshold.

    Args:
        samples (np.ndarray): Input audio
        sample_rate (int): Sample rate in Hz
        tone_duration (float): Expected tone duration in seconds (used for validation)
        pause_duration (float): Expected pause duration in seconds (used for validation)

    Returns:
        list: List of audio segments, each containing one DTMF tone
    """
    # Compute short-time energy with smaller frames for better resolution
    frame_size = int(0.005 * sample_rate)  # 5ms frames
    if frame_size < 1:
        frame_size = 1

    n_frames = len(samples) // frame_size

    energies = []
    for i in range(n_frames):
        frame = samples[i*frame_size:(i+1)*frame_size]
        energy = np.mean(frame ** 2)
        energies.append(energy)

    energies = np.array(energies)

    if len(energies) == 0:
        return []

    # Find tone segments using dynamic threshold
    # Use a more aggressive threshold to avoid noise
    max_energy = np.max(energies)
    threshold = max_energy * 0.05  # 5% of max energy
    tone_mask = energies > threshold

    # Apply hysteresis to smooth out small dips
    min_tone_frames = int(0.04 * sample_rate / frame_size)  # Minimum 40ms tone

    # Dilate to close small gaps
    for i in range(1, len(tone_mask) - 1):
        if tone_mask[i-1] and tone_mask[i+1]:
            tone_mask[i] = True

    # Find transitions (onset and offset)
    transitions = np.diff(tone_mask.astype(int))
    onsets = np.where(transitions == 1)[0]
    offsets = np.where(transitions == -1)[0]

    # Handle edge cases: if tone starts at beginning, add implicit onset
    if len(tone_mask) > 0 and tone_mask[0]:
        onsets = np.concatenate([[0], onsets])

    # Handle edge cases: if tone extends to end, add implicit offset
    if len(tone_mask) > 0 and tone_mask[-1]:
        offsets = np.concatenate([offsets, [len(tone_mask) - 1]])

    # Ensure we have matching pairs
    if len(offsets) < len(onsets):
        offsets = np.append(offsets, len(tone_mask) - 1)
    if len(onsets) < len(offsets):
        onsets = np.concatenate([[0], onsets])

    # Extract segments
    segments = []
    for i, (onset, offset) in enumerate(zip(onsets, offsets)):
        if offset - onset < min_tone_frames:
            continue  # Skip very short segments
        start_sample = onset * frame_size
        end_sample = min((offset + 1) * frame_size, len(samples))
        segment = samples[start_sample:end_sample]
        if len(segment) > 0:
            segments.append(segment)

    return segments


def decode_dtmf_audio(samples, sample_rate=SAMPLE_RATE):
    """
    Decode audio containing DTMF tones to a digit string.

    Args:
        samples (np.ndarray): Input audio
        sample_rate (int): Sample rate in Hz

    Returns:
        str: Decoded digit string
    """
    # Segment into individual tones
    segments = segment_dtmf_tones(samples, sample_rate)

    digits = []
    for segment in segments:
        row_freq, col_freq = detect_dtmf_frequencies(segment, sample_rate)
        if row_freq is not None and col_freq is not None:
            digit = freqs_to_digit(row_freq, col_freq)
            if digit is not None:
                digits.append(digit)

    return ''.join(digits)


# Roundtrip test
if __name__ == "__main__":
    import tempfile
    import os

    print("DTMF Codec Roundtrip Test")
    print("=" * 50)

    # Test digits
    test_digits = "123456789*0#ABCD"
    print(f"Original:  {test_digits}")

    # Encode to audio
    audio = encode_dtmf_string(test_digits,
                              tone_duration=0.15,
                              pause_duration=0.10)
    print(f"Encoded {len(audio)} samples ({len(audio)/SAMPLE_RATE:.2f}s)")

    # Write to temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_file = f.name

    try:
        write_wav(temp_file, audio)
        print(f"Written to {temp_file}")

        # Read back
        loaded_audio, sr = read_wav(temp_file)
        print(f"Loaded {len(loaded_audio)} samples at {sr} Hz")

        # Decode
        decoded = decode_dtmf_audio(loaded_audio, sr)
        print(f"Decoded:   {decoded}")

        # Check result
        if decoded == test_digits:
            print("\nRoundtrip: PASS")
        else:
            print("\nRoundtrip: FAIL")
            print(f"  Mismatched: {len(set(test_digits) & set(decoded))} digits matched")

    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
