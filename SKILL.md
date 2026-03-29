---
name: dtmf-codec
description: >
  Encode and decode DTMF (Dual-Tone Multi-Frequency) signaling, also known as touch-tone
  or phone dialing tones. Implements ITU-T Q.23/Q.24 standard telephone keypad signaling
  with a 4x4 frequency grid (697-941 Hz low group, 1209-1633 Hz high group). Supports
  encoding digit strings to dual-tone audio (WAV files), and decoding DTMF audio back
  to digits using the Goertzel algorithm. Handles standard digits (0-9, *, #, A-D) with
  proper tone and pause timing. Ideal for telephone signaling simulation, telephony
  applications, amateur radio, and audio signaling systems.
---

# DTMF Signaling Codec

DTMF (Dual-Tone Multi-Frequency) is the standardized technology behind telephone keypads.
When you press a key on a rotary phone or modern telephone, it generates two simultaneous
sine wave tones—one from the low-frequency group and one from the high-frequency group.
This two-frequency approach (hence "dual-tone") was introduced by AT&T in 1963 and became
the international standard for telephone signaling (ITU-T Q.23/Q.24).

## Quick Reference: The DTMF Signal

A DTMF tone consists of:
- **Two frequencies** combined: one "row" frequency and one "column" frequency
- **Tone duration**: typically 65-100ms (this implementation uses 100ms by default)
- **Pause**: typically 65-100ms of silence between digit tones
- **Amplitude**: both tones at equal amplitude in the final signal

## DTMF Frequency Grid

The standard DTMF keypad uses a 4×4 matrix of frequencies:

```
        1209 Hz  1336 Hz  1477 Hz  1633 Hz
697 Hz:   1        2        3        A
770 Hz:   4        5        6        B
852 Hz:   7        8        9        C
941 Hz:   *        0        #        D
```

**Low-group (row) frequencies**: 697, 770, 852, 941 Hz
**High-group (column) frequencies**: 1209, 1336, 1477, 1633 Hz

When you press the "5" key, you hear 770 Hz + 1336 Hz combined.
When you press the "*" key, you hear 941 Hz + 1209 Hz combined.

## How to Use This Skill

### Encoding

Convert a string of digits to audio using `dtmf_encode.py`:

```bash
python3 scripts/dtmf_encode.py "5551234#" output.wav
```

Options:
- `--tone-duration MS`: Duration of each tone (default: 100 ms)
- `--pause-duration MS`: Silence between tones (default: 100 ms)
- `--sample-rate RATE`: Sample rate in Hz (default: 44100)

Output is a 16-bit mono WAV file suitable for playback or transmission.

#### Typical Workflow: Encoding

1. Prepare a digit string (e.g., a phone number or command code)
2. Run the encoder with appropriate durations (100ms tones + 100ms pauses are standard)
3. The output WAV can be:
   - Played over a speaker or telephone handset
   - Transmitted over a radio channel (amateur/professional)
   - Embedded in a larger audio file
   - Used as test data for telephony applications

### Decoding

Convert audio containing DTMF tones back to digits using `dtmf_decode.py`:

```bash
python3 scripts/dtmf_decode.py input.wav
```

Optionally save the decoded string to a file:

```bash
python3 scripts/dtmf_decode.py input.wav decoded.txt
```

The decoder uses the **Goertzel algorithm** to detect specific frequencies efficiently.
It processes the audio in short segments, identifies the dominant row and column
frequencies in each segment, and maps them back to the original digit.

#### Typical Workflow: Decoding

1. Record or obtain audio containing DTMF tones (from a phone line, radio, etc.)
2. Run the decoder on the WAV file
3. It outputs the decoded digit string to stdout or a file
4. Use the decoded digits for further processing (dial routing, command execution, etc.)

### Typical Workflow

A complete roundtrip looks like:

```bash
# Encode phone number to audio
python3 scripts/dtmf_encode.py "18005551234" phone_call.wav

# (Play, transmit, or record phone_call.wav)

# Decode the audio back to digits
python3 scripts/dtmf_decode.py phone_call.wav
# Output: 18005551234
```

## Technical Details

### Encoding Algorithm

1. For each digit in the input string:
   - Look up the row and column frequencies from the DTMF grid
   - Generate sine waves at both frequencies
   - Combine them with equal amplitude
   - Normalize to prevent clipping
   - Append a pause (silence)
2. Concatenate all tones into a single audio stream
3. Write as 16-bit mono WAV at the specified sample rate

### Decoding Algorithm

The decoder uses the **Goertzel algorithm**, a computationally efficient method for
detecting specific frequencies in real-time or streaming audio. It's more efficient
than FFT for this use case because we only need to check 8 specific frequencies.

1. Segment the audio into frames (10ms windows)
2. For each segment:
   - Compute energy at all 8 DTMF frequencies using Goertzel
   - Identify the strongest row frequency and strongest column frequency
   - Verify the signal meets energy and "twist" (amplitude ratio) thresholds
   - Map the frequency pair to a digit
3. Concatenate decoded digits into the output string

**Energy threshold**: Minimum signal power to be considered a valid tone (avoids noise)
**Twist detection**: Verifies that high and low group energies are within 1.4× ratio
(DTMF spec allows some variation in tone amplitudes but not extreme imbalance)

## Dependencies

- **numpy**: For signal processing and array operations
- **wave**: Standard library module for WAV file I/O

No external audio libraries required—all DSP is implemented from first principles.

## Limitations and Notes

- **Noise robustness**: Works well with clean signals. High noise may degrade accuracy.
- **Tone overlap**: Assumes tones are well-separated (standard 65-100ms with pauses).
  Overlapping tones from the speaker may confuse the decoder.
- **Frequency tolerance**: Detected frequencies within ±20 Hz of standard DTMF
  frequencies are accepted (allows for frequency drift in analog systems).
- **Sample rate flexibility**: Works at any sample rate (44.1 kHz typical, 8 kHz for
  telephony, etc.) but encoding at 44.1 kHz is recommended for quality.

## Standards Reference

- **ITU-T Q.23**: Technical features of Push Button Telephone Sets
- **ITU-T Q.24**: Multifrequency code signal transmission
- **Bell System Technical Journal**: Original DTMF specifications (1963)

## See Also

This skill is part of a family of audio codec skills for signal processing:
- **apt-codec**: NOAA weather satellite imagery transmission
- **fax-codec**: Facsimile transmission (Group 3 fax)
- **sstv-codec**: Slow-scan television for amateur radio
- **rtty-codec**: Radioteletype (Baudot) text transmission
- **data-modem**: Binary file transmission via FSK modem
