#!/usr/bin/env python3
"""
DTMF Decoder CLI

Decodes DTMF tones from a WAV audio file back to digit string.
"""

import argparse
import sys
from dtmf_common import read_wav, decode_dtmf_audio


def main():
    parser = argparse.ArgumentParser(
        description='Decode DTMF tones from WAV audio',
        epilog='Example: %(prog)s input.wav decoded.txt',
    )

    parser.add_argument(
        'input',
        help='Input WAV filename containing DTMF tones',
    )

    parser.add_argument(
        'output',
        nargs='?',
        help='Output text filename (optional; prints to stdout if omitted)',
    )

    args = parser.parse_args()

    try:
        # Read WAV
        print(f"Loading: {args.input}", file=sys.stderr)
        samples, sample_rate = read_wav(args.input)
        print(f"Loaded: {len(samples)} samples at {sample_rate} Hz", file=sys.stderr)

        # Decode
        print("Decoding...", file=sys.stderr)
        digits = decode_dtmf_audio(samples, sample_rate)

        # Output
        if args.output:
            with open(args.output, 'w') as f:
                f.write(digits)
            print(f"Written: {args.output}", file=sys.stderr)
        else:
            print(digits)

    except IOError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
