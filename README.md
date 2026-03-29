# DTMF Codec

Encode and decode DTMF (Dual-Tone Multi-Frequency) signaling—the technology behind telephone keypads, also known as "touch-tone" or phone dialing tones.

## What Is DTMF?

DTMF is the standardized system used in telephone networks since the 1960s to signal digit presses. When you press a key on a phone keypad, it generates two simultaneous sine wave tones—one from a low-frequency group (697–941 Hz) and one from a high-frequency group (1209–1633 Hz). The combination of these two frequencies uniquely identifies each digit (0–9) and symbol (*, #, A–D).

## Features

- **ITU-T Q.23/Q.24 compliant**: Standard telephony signaling frequencies
- **Dual-frequency detection**: Uses the Goertzel algorithm for efficient frequency detection
- **Flexible timing**: Configurable tone and pause durations (default: 100 ms each)
- **Clean output**: 16-bit mono WAV files
- **Robust decoding**: Energy thresholds and twist detection for reliable digit identification
- **All symbols**: Supports 0–9, *, #, A–D (standard 4×4 keypad grid)
- **No external audio libraries**: Uses only numpy and Python's built-in `wave` module

## Quick Start

### Encoding: Digits → Audio

```bash
python3 scripts/dtmf_encode.py "5551234#" output.wav
```

Creates a WAV file with DTMF tones for the digits "5551234#".

**Options:**
- `--tone-duration MS`: Length of each tone (default: 100)
- `--pause-duration MS`: Silence between tones (default: 100)
- `--sample-rate RATE`: Output sample rate in Hz (default: 44100)

### Decoding: Audio → Digits

```bash
python3 scripts/dtmf_decode.py input.wav
```

Reads a WAV file, detects DTMF tones, and outputs the decoded digit string.

```bash
python3 scripts/dtmf_decode.py input.wav output.txt
```

Save the decoded digits to a text file.

## The DTMF Keypad

The standard 4×4 frequency matrix:

```
        1209 Hz  1336 Hz  1477 Hz  1633 Hz
697 Hz:   1        2        3        A
770 Hz:   4        5        6        B
852 Hz:   7        8        9        C
941 Hz:   *        0        #        D
```

Each key produces a unique combination of row and column frequencies:
- **"5"** = 770 Hz + 1336 Hz
- **"*"** = 941 Hz + 1209 Hz
- **"#"** = 941 Hz + 1477 Hz

## How It Works

### Encoding

The encoder generates sine waves at two frequencies and combines them:

```
For digit "5" (770 Hz + 1336 Hz):
├─ Generate 770 Hz sine wave for 100 ms
├─ Generate 1336 Hz sine wave for 100 ms
├─ Combine with equal amplitude
├─ Normalize to prevent clipping
└─ Add 100 ms of silence (pause)
```

All tones in the output stream are concatenated to form the final audio.

### Decoding

The decoder identifies tones using the **Goertzel algorithm**, an efficient method for
detecting specific frequencies in audio:

```
For each 10 ms audio frame:
├─ Compute energy at all 8 DTMF frequencies using Goertzel
├─ Find the strongest row frequency (697, 770, 852, or 941 Hz)
├─ Find the strongest column frequency (1209, 1336, 1477, or 1633 Hz)
├─ Verify energy is above threshold (avoid noise)
├─ Verify amplitude ratio between groups is within spec ("twist" check)
└─ Map frequency pair to digit

Result: Concatenated digit string
```

## Example Usage

### Basic Encoding

```bash
# Encode a phone number
python3 scripts/dtmf_encode.py "18005551234" phone_number.wav

# Play the WAV to verify
aplay phone_number.wav  # or 'paplay' on Fedora, 'afplay' on macOS
```

### Basic Decoding

```bash
# Decode audio recorded from a phone line
python3 scripts/dtmf_decode.py recorded_call.wav

# Save to file
python3 scripts/dtmf_decode.py recorded_call.wav decoded.txt
```

### Custom Timing

ITU-T specifications allow tone durations as short as 65 ms. To encode faster sequences:

```bash
# Fast DTMF: 65 ms tones + 65 ms pauses
python3 scripts/dtmf_encode.py "1234567890" fast.wav --tone-duration 65 --pause-duration 65

# Slow DTMF: 200 ms tones + 150 ms pauses (for noisy lines)
python3 scripts/dtmf_encode.py "1234567890" slow.wav --tone-duration 200 --pause-duration 150
```

### Using as a Module

```python
from dtmf_common import encode_dtmf_string, write_wav, read_wav, decode_dtmf_audio

# Encode
audio = encode_dtmf_string("5551234#", tone_duration=0.1, pause_duration=0.1)
write_wav("output.wav", audio)

# Decode
samples, sample_rate = read_wav("output.wav")
digits = decode_dtmf_audio(samples, sample_rate)
print(digits)  # Output: 5551234#
```

## File Structure

```
dtmf/
├── scripts/
│   ├── dtmf_common.py    # Shared encoding/decoding library
│   ├── dtmf_encode.py    # CLI encoder
│   └── dtmf_decode.py    # CLI decoder
├── SKILL.md              # Skill documentation
└── README.md             # This file
```

## Dependencies

- **Python 3.6+**
- **numpy**: Numerical arrays and signal processing
- **wave**: Standard library (included in Python)

Install numpy:

```bash
pip install numpy
```

## Testing

The `dtmf_common.py` module includes a roundtrip test. Run it to verify the codec:

```bash
python3 scripts/dtmf_common.py
```

Expected output:

```
DTMF Codec Roundtrip Test
==================================================
Original:  123456789*0#ABCD
Encoded 100320 samples (2.27s)
Written to /tmp/tmpXXXXXX.wav
Loaded 100320 samples at 44100 Hz
Decoding...
Decoded:   123456789*0#ABCD

Roundtrip: PASS
```

## Technical Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Row frequencies | 697, 770, 852, 941 Hz | Low-frequency group |
| Column frequencies | 1209, 1336, 1477, 1633 Hz | High-frequency group |
| Tone duration | 65–100 ms | ITU-T minimum: 65 ms; default: 100 ms |
| Pause duration | 65–100 ms | ITU-T minimum: 65 ms; default: 100 ms |
| Amplitude ratio ("twist") | ±4 dB | Max allowed difference in energy |
| Energy threshold | 0.02 (relative) | Minimum signal power to detect tone |
| Frequency tolerance | ±20 Hz | Acceptable deviation from standard frequencies |
| Sample rate | Any (typical: 44100 Hz) | Telephony often uses 8000 Hz |
| Output format | 16-bit mono WAV | Compatible with phone systems and audio software |

## Standards References

- **ITU-T Q.23** — Technical features of Push Button Telephone Sets
- **ITU-T Q.24** — Multifrequency code signal transmission
- **Bell System Technical Journal** (1963) — Original DTMF specification
- **AT&T Technical Publication 41007** — DTMF implementation guide

## Use Cases

1. **Telephone simulation**: Generate tones for automated phone systems
2. **Testing**: Validate DTMF decoders in telecommunications equipment
3. **Amateur radio**: Send command codes over radio using DTMF signaling
4. **Access control**: Trigger door locks or alarms via DTMF commands
5. **Audio signaling**: Embed command codes in recordings or radio broadcasts
6. **Data encoding**: Use DTMF as a basic encoding method for serial data over audio

## Limitations

- **Noise sensitivity**: Works best with clean signals; noisy audio may reduce accuracy
- **Tone overlap**: Assumes well-separated tones with pauses; overlapping tones confuse detection
- **Analog drift**: Real telephone systems may have frequency drift; decoder tolerates ±20 Hz
- **Single digit at a time**: Decoder identifies one digit per tone segment; simultaneous tones are not supported

## License

This skill is provided as-is for educational and professional use in audio signal processing.

## See Also

Other audio codec skills in this family:
- **apt-codec** — NOAA weather satellite image transmission
- **fax-codec** — ITU-T Group 3 facsimile (fax) transmission
- **sstv-codec** — Slow-scan television for amateur radio
- **rtty-codec** — Radioteletype (Baudot) transmission
- **data-modem** — Binary file transmission via FSK modem
