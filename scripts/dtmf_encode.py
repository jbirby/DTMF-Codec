#!/usr/bin/env python3
"""
DTMF Encoder CLI

Encodes a string of DTMF digits to a WAV audio file.
"""

import argparse
import sys
from dtmf_common import (
    encode_dtmf_string,
    write_wav,
    DEFAULT_TONE_DURATION,
    DEFAULT_PAUSE_DURATION,
    SAMPLE_RATE,
)


def main():
    parser = argparse.ArgumentParser(
        description='Encode DTMF digits to WAV audio',
        epilog='Example: %(prog)s "5551234#" output.wav --tone-duration 100',
    )

    parser.add_argument(
        'digits',
        help='String of DTMF digits to encode (0-9, *, #, A-D)',
    )

    parser.add_argument(
        'output',
        help='Output WAV filename',
    )

    parser.add_argument(
        '--tone-duration',
        type=int,
        default=int(DEFAULT_TONE_DURATION * 1000),
        help='Duration of each tone in milliseconds (default: 100)',
        metavar='MS',
    )

    parser.add_argument(
        '--pause-duration',
        type=int,
        default=int(DEFAULT_PAUSE_DURATION * 1000),
        help='Duration of silence between tones in milliseconds (default: 100)',
        metavar='MS',
    )

    parser.add_argument(
        '--sample-rate',
        type=int,
        default=SAMPLE_RATE,
        help='Sample rate in Hz (default: 44100)',
        metavar='RATE',
    )

    args = parser.parse_args()

    # Convert milliseconds to seconds
    tone_duration = args.tone_duration / 1000.0
    pause_duration = args.pause_duration / 1000.0

    try:
        # Encode
        print(f"Encoding: {args.digits}")
        audio = encode_dtmf_string(
            args.digits,
            tone_duration=tone_duration,
            pause_duration=pause_duration,
            sample_rate=args.sample_rate,
        )

        # Write
        write_wav(args.output, audio, args.sample_rate)

        duration = len(audio) / args.sample_rate
        print(f"Written: {args.output}")
        print(f"Duration: {duration:.2f}s")
        print(f"Sample rate: {args.sample_rate} Hz")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
