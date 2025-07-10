import numpy as np
import PySpin
import os

def raw_conversion(raw_image_path, converted_image_path, width=5472, height=3648, width_offset=0, height_offset=0):
    """
    Convert a raw image to jpg format.

    :param raw_image_path: Path to the input raw image file.
    :param converted_image_path: Path to save the output jpg/png/tiff image file.
    """
    offline_data = np.fromfile(raw_image_path, dtype=np.ubyte)
    load_image = PySpin.Image.Create(width, height, width_offset, height_offset, PySpin.PixelFormat_BayerRG12Packed, offline_data)

    processor = PySpin.ImageProcessor()
    # By default, if no specific color processing algorithm is set, the image
    # processor will default to NEAREST_NEIGHBOR method.
    processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)

    result_image = processor.Convert(load_image, PySpin.PixelFormat_RGB16)
    # Save image
    result_image.Save(converted_image_path)


if __name__ == "__main__":
    # Example usage
    raw_image_path = "/mnt/ssd/Acquisition-24284605-0.raw"  # Replace with your raw image path
    converted_image_path = "Acquisition-24284605-0_.jpg"   # Replace with your desired jpg/png/tiff output path

    raw_conversion(raw_image_path, converted_image_path)
    

    