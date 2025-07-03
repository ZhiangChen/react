# Teledyne Flir Camera

## Camera Info
Mode: BFS-U3-200S6C-C  
Specs: https://www.teledynevisionsolutions.com/products/blackfly-s-usb3/?model=BFS-U3-200S6C-C&vertical=machine%20vision&segment=iis  
Lens: https://www.edmundoptics.com/p/8mm-focal-length-lens-1quot-sensor-format/17859/?srsltid=AfmBOooZbAFPRv3TpqxfrttE8dY1yQFuPiGTMLJu9K_HqxB5HJYAxQzZ  
HFOV: 79°  
VFOV: 57°  


## Spinnaker SDK
**Installation**: https://www.teledynevisionsolutions.com/support/support-center/application-note/iis/using-spinnaker-on-arm-and-embedded-systems/  

**SpinView**  
Spinnaker does not support OpenGL on ARM: Limitations Using ARM
Limitations Using ARM: https://www.teledynevisionsolutions.com/support/support-center/application-note/iis/using-spinnaker-on-arm-and-embedded-systems/

We can force Software Rendering and bypass OpenGL/GPU entirely to run SpinView:
```
(base) zhiangchen@raspberrypi:/opt/spinnaker/bin $ LIBGL_ALWAYS_SOFTWARE=1 ./spinview
```
**Guide and documentation** can be found in `flir_camera/docs`. The guide is important to read as it introduces basic architecture of the APIs and rules. For example, it is important to release an image pointer after usage, including conversion or saving. 

## Examples
1. [Acquisition_jpg.py](examples/Acquisition_jpg.py) demonstrates how to grab an image and save it as a jpg.  

2. [Acquisition_jpg.py](examples/Acquisition_raw.py) demonstrates how to grab an image and save it as a raw. From these two examples, you can measure the photo capture and writing speed in ssd. The average photo time for jpg is 0.78 seconds, and the average photo time for raw is 0.08 seconds. The difference is primarily caused by the conversion from raw to jpg.    

    `PySpin.Image.Save()` is a synchronous function at the application level—it blocks the program until the image is handed off to the operating system. However, the actual file I/O is buffered: the image data is first written to the Linux page cache. As a result, disk writes appear fast initially, regardless of whether you're writing to an SSD or a microSD card. But once the cache fills up, the true write speed of the storage device becomes the bottleneck. At that point, the SSD maintains high throughput, while the microSD card’s slower write performance causes noticeable delays.

3. [raw_conversion.py](examples/raw_conversion.py) converts raw image files to jpg/png/tif image formats. 

4. [camera_configuration.py](examples/camera_configuration.py)

    - continuous auto exposure with a maximum exposure time
    - auto gain vs acquisition mode 
    - single shot vs continous shot 
  basically, you need to understand all the features 

    **What is a camera node?**


## Utils
[writing_test.py](writing_test.py) estimates the average writing speed in micro sd card and ssd. 