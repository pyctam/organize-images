#!/usr/bin/env python3

import argparse
import os
import sys

from PIL import Image


def parse_rgb(value):
    """Parse an RGB color in the form R,G,B."""
    try:
        parts = value.split(",")

        if len(parts) != 3:
            raise ValueError

        rgb = tuple(int(part.strip()) for part in parts)

        if any(channel < 0 or channel > 255 for channel in rgb):
            raise ValueError

        return rgb

    except ValueError:
        raise argparse.ArgumentTypeError(
            "RGB color must be in the format R,G,B "
            "with each value between 0 and 255."
        )


def non_background_bbox(image, background_rgb):
    """
    Scan the image pixel-by-pixel and return the bounding box of all
    pixels that do not match background_rgb.

    Returns:
        (left, top, right, bottom)
        where right and bottom are exclusive, matching Pillow's crop()
        convention.

    Returns None if the entire image is background.
    """

    # Convert to RGB so that every pixel can be compared consistently.
    rgb_image = image.convert("RGB")

    width, height = rgb_image.size
    pixels = rgb_image.load()

    left = width
    top = height
    right = -1
    bottom = -1

    for y in range(height):
        for x in range(width):
            if pixels[x, y] != background_rgb:
                if x < left:
                    left = x

                if x > right:
                    right = x

                if y < top:
                    top = y

                if y > bottom:
                    bottom = y

    # No non-background pixels were found.
    if right == -1:
        return None

    # Convert right/bottom to Pillow's exclusive-coordinate convention.
    return left, top, right + 1, bottom + 1


def expand_bbox(bbox, image_size, offset):
    """Expand a bounding box by offset pixels, clamped to the image."""
    left, top, right, bottom = bbox
    width, height = image_size

    left = max(0, left - offset)
    top = max(0, top - offset)
    right = min(width, right + offset)
    bottom = min(height, bottom + offset)

    return left, top, right, bottom


def output_path(input_path):
    """Create the output filename by adding '-trimmed' before the extension."""
    directory, filename = os.path.split(input_path)
    name, extension = os.path.splitext(filename)

    return os.path.join(
        directory,
        f"{name}-trimmed{extension}"
    )


def trim_image(input_path, background_rgb, offset):
    if offset < 0:
        raise ValueError("Offset must be greater than or equal to zero.")

    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Image does not exist: {input_path}")

    with Image.open(input_path) as image:
        original_size = image.size

        bbox = non_background_bbox(image, background_rgb)

        if bbox is None:
            raise ValueError(
                "The entire image matches the supplied background color. "
                "There is nothing to trim."
            )

        trimmed_bbox = expand_bbox(
            bbox,
            image.size,
            offset
        )

        # Use the original image for cropping so that formats such as
        # PNG retain their original mode/transparency where possible.
        cropped = image.crop(trimmed_bbox)

        output = output_path(input_path)

        # Avoid accidentally modifying the original file.
        cropped.save(output)

    return output, original_size, bbox, trimmed_bbox


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Trim an image to the bounding box of pixels that do not "
            "match the supplied background RGB color."
        )
    )

    parser.add_argument(
        "image",
        help="Path to the input image."
    )

    parser.add_argument(
        "background",
        type=parse_rgb,
        help="Background RGB color, for example: 255,255,255"
    )

    parser.add_argument(
        "offset",
        type=int,
        help="Number of pixels to preserve around the detected content. Must be >= 0."
    )

    args = parser.parse_args()

    if args.offset < 0:
        parser.error("offset must be greater than or equal to zero.")

    try:
        output, original_size, bbox, trimmed_bbox = trim_image(
            args.image,
            args.background,
            args.offset
        )

        print(f"Input:       {args.image}")
        print(f"Original:    {original_size[0]}x{original_size[1]}")
        print(f"Background:  RGB{args.background}")
        print(f"Offset:      {args.offset}px")
        print(f"Content box: {bbox}")
        print(f"Crop box:    {trimmed_bbox}")
        print(f"Output:      {output}")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

