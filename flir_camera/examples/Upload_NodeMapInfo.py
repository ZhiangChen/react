import yaml
import PySpin
import sys

def read_yaml(file_path):
    # Read a YAML file and return its content as a dictionary.
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data

configuration_file = "data/field_mapping_camera_configuration.yaml"
config = read_yaml(configuration_file)

def configure_custom_image_settings(cam):
    """
    Configures a number of settings on the camera including offsets X and Y,
    width, height, and pixel format. These settings must be applied before
    BeginAcquisition() is called; otherwise, those nodes would be read only.
    Also, it is important to note that settings are applied immediately.
    This means if you plan to reduce the width and move the x offset accordingly,
    you need to apply such changes in the appropriate order.

    :param cam: Camera to configure settings on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print('\n*** CONFIGURING CUSTOM IMAGE SETTINGS ***\n')

    global config

    try:
        result = True

        # Set Exposure Auto
        # check if exposure auto is in config dictionary
        if 'Exposure Auto' in config['Root']['Acquisition Control']:
            exposure_auto = config['Root']['Acquisition Control']['Exposure Auto']
            if cam.ExposureAuto.GetAccessMode() == PySpin.RW:
                if exposure_auto == 'Continuous':
                    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
                elif exposure_auto == False:
                    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                    # Set exposure time if exposure auto is off
                    if 'Exposure Time' in config['Root']['Acquisition Control']:
                        exposure_time = config['Root']['Acquisition Control']['Exposure Time']
                        if cam.ExposureTime.GetAccessMode() == PySpin.RW:
                            cam.ExposureTime.SetValue(exposure_time)
                            print('Exposure time set to %f...' % cam.ExposureTime.GetValue())
                elif exposure_auto == 'Once':
                    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Once)
                else:
                    print('Unsupported Exposure Auto: %s' % exposure_auto)
                print('Exposure Auto set to %s...' % cam.ExposureAuto.GetCurrentEntry().GetSymbolic())

        # Set Acquisition Frame Rate Enable
        # check if acquisition frame rate enable is in config dictionary
        if 'Acquisition Frame Rate Enable' in config['Root']['Acquisition Control']:
            acquisition_frame_rate_enable = config['Root']['Acquisition Control']['Acquisition Frame Rate Enable']
            if cam.AcquisitionFrameRateEnable.GetAccessMode() == PySpin.RW:
                cam.AcquisitionFrameRateEnable.SetValue(acquisition_frame_rate_enable)
                print('Acquisition Frame Rate Enable set to %s...' % cam.AcquisitionFrameRateEnable.GetValue())

        # Set Acquisition Frame Rate
        # check if acquisition frame rate is in config dictionary
        if 'Acquisition Frame Rate' in config['Root']['Acquisition Control']:
            acquisition_frame_rate = config['Root']['Acquisition Control']['Acquisition Frame Rate']
            if cam.AcquisitionFrameRate.GetAccessMode() == PySpin.RW:
                cam.AcquisitionFrameRate.SetValue(acquisition_frame_rate)
                print('Acquisition Frame Rate set to %f...' % cam.AcquisitionFrameRate.GetValue())
    
            
        # Apply gamma enable
        # check if gamma enable is in config dictionary
        if 'Gamma Enable' in config['Root']['Analog Control']:
            gamma_enable = config['Root']['Analog Control']['Gamma Enable']
            if cam.GammaEnable.GetAccessMode() == PySpin.RW:
                cam.GammaEnable.SetValue(gamma_enable)
                print('Gamma enable set to %s...' % cam.GammaEnable.GetValue())

            # Apply gamma
            # check if gamma is in config dictionary
            if 'Gamma' in config['Root']['Analog Control']:
                gamma_value = config['Root']['Analog Control']['Gamma']
                if cam.Gamma.GetAccessMode() == PySpin.RW:
                    cam.Gamma.SetValue(gamma_value)
                    print('Gamma set to %f...' % cam.Gamma.GetValue())



        # Apply pixel format
        # check if pixel format is in config dictionary
        if 'Pixel Format' in config['Root']['Image Format Control']:
            pixel_format = config['Root']['Image Format Control']['Pixel Format']
            if pixel_format == "BayerRG12Packed":
                pyspin_pixel_format = PySpin.PixelFormat_BayerRG12Packed
                if cam.PixelFormat.GetAccessMode() == PySpin.RW:
                    cam.PixelFormat.SetValue(pyspin_pixel_format)
                    print('Pixel format set to %s...' % cam.PixelFormat.GetCurrentEntry().GetSymbolic())

        # Apply minimum to offset X
        # check if offset X is in config dictionary
        if 'Offset X' in config['Root']['Image Format Control']:
            offset_x = config['Root']['Image Format Control']['Offset X']
            if cam.OffsetX.GetAccessMode() == PySpin.RW:
                cam.OffsetX.SetValue(offset_x)
                print('Offset X set to %d...' % cam.OffsetX.GetValue())


        # Apply minimum to offset Y
        # check if offset Y is in config dictionary
        if 'Offset Y' in config['Root']['Image Format Control']:
            offset_y = config['Root']['Image Format Control']['Offset Y']
            if cam.OffsetY.GetAccessMode() == PySpin.RW:
                cam.OffsetY.SetValue(offset_y)
                print('Offset Y set to %d...' % cam.OffsetY.GetValue())

        # Set max width
        # check if width max is in config dictionary
        if 'Width Max' in config['Root']['Image Format Control']:
            width_max = config['Root']['Image Format Control']['Width Max']
            #if cam.WidthMax.GetAccessMode() == PySpin.RW:
            cam.WidthMax.ImposeMax(width_max)
            print('Width max set to %i...' % cam.WidthMax.GetValue())



        # Set max height
        # check if height max is in config dictionary
        if 'Height Max' in config['Root']['Image Format Control']:
            height_max = config['Root']['Image Format Control']['Height Max']
            #if cam.HeightMax.GetAccessMode() == PySpin.RW:
            cam.HeightMax.ImposeMax(height_max)
            print('Height max set to %i...' % cam.HeightMax.GetValue())

        # Set width
        # check if width is in config dictionary
        if 'Width' in config['Root']['Image Format Control']:
            width = config['Root']['Image Format Control']['Width']
            if cam.Width.GetAccessMode() == PySpin.RW:
                cam.Width.SetValue(width)
                print('Width set to %i...' % cam.Width.GetValue())  

        # Set height
        # check if height is in config dictionary
        if 'Height' in config['Root']['Image Format Control']:
            height = config['Root']['Image Format Control']['Height']
            if cam.Height.GetAccessMode() == PySpin.RW:
                cam.Height.SetValue(height)
                print('Height set to %i...' % cam.Height.GetValue())

        # Set ADC Bit Depth
        # check if ADC Bit Depth is in config dictionary
        if 'ADC Bit Depth' in config['Root']['Image Format Control']:
            adc_bit_depth = config['Root']['Image Format Control']['ADC Bit Depth']
            if cam.AdcBitDepth.GetAccessMode() == PySpin.RW:
                if adc_bit_depth == 'Bit12':
                    cam.AdcBitDepth.SetValue(PySpin.AdcBitDepth_Bit12)
                elif adc_bit_depth == 'Bit10':
                    cam.AdcBitDepth.SetValue(PySpin.AdcBitDepth_Bit10)
                else:
                    print('Unsupported ADC Bit Depth: %s' % adc_bit_depth)
                print('ADC Bit Depth set to %s...' % cam.AdcBitDepth.GetCurrentEntry().GetSymbolic())

        # Set RGB Transform Light Source
        # check if RGB Transform Light Source is in config dictionary
        if 'RGB Transform Light Source' in config['Root']['Color Transformation Control']:
            rgb_transform_light_source = config['Root']['Color Transformation Control']['RGB Transform Light Source']
            if cam.RgbTransformLightSource.GetAccessMode() == PySpin.RW:
                if rgb_transform_light_source == 'General':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_General)
                elif rgb_transform_light_source == 'Cloudy':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_Cloudy6500K)
                elif rgb_transform_light_source == 'CoolFluorescent':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_CoolFluorescent4000K)
                elif rgb_transform_light_source == 'Daylight':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_Daylight5000K)
                elif rgb_transform_light_source == 'Shade':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_Shade8000K)
                elif rgb_transform_light_source == 'Tungsten':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_Tungsten2800K)
                elif rgb_transform_light_source == 'WarmFluorescent':
                    cam.RgbTransformLightSource.SetValue(PySpin.RgbTransformLightSource_WarmFluorescent3000K)
                else:
                    print('Unsupported RGB Transform Light Source: %s' % rgb_transform_light_source)
                print('RGB Transform Light Source set to %s...' % cam.RgbTransformLightSource.GetCurrentEntry().GetSymbolic())

        # Set white balance auto profile
        # check if white balance auto profile is in config dictionary
        if 'White Balance Auto Profile' in config['Root']['Auto Algorithm Control']:
            white_balance_auto_profile = config['Root']['Auto Algorithm Control']['White Balance Auto Profile']
            if cam.BalanceWhiteAutoProfile.GetAccessMode() == PySpin.RW:
                if white_balance_auto_profile == 'Indoor':
                    cam.BalanceWhiteAutoProfile.SetValue(PySpin.BalanceWhiteAutoProfile_Indoor)
                elif white_balance_auto_profile == 'Outdoor':
                    cam.BalanceWhiteAutoProfile.SetValue(PySpin.BalanceWhiteAutoProfile_Outdoor)
                else:
                    print('Unsupported White Balance Auto Profile: %s' % white_balance_auto_profile)
                print('White Balance Auto Profile set to %s...' % cam.BalanceWhiteAutoProfile.GetCurrentEntry().GetSymbolic())

        # Set white balance auto damping
        # check if white balance auto damping is in config dictionary
        if 'White Balance Auto Damping' in config['Root']['Auto Algorithm Control']:
            white_balance_auto_damping = config['Root']['Auto Algorithm Control']['White Balance Auto Damping']
            if cam.BalanceWhiteAutoDamping.GetAccessMode() == PySpin.RW:
                cam.BalanceWhiteAutoDamping.SetValue(white_balance_auto_damping)
                print('White Balance Auto Damping set to %f...' % cam.BalanceWhiteAutoDamping.GetValue())

        # Set Exposure Time Lower Limit
        # check if exposure time lower limit is in config dictionary
        if 'Exposure Time Lower Limit' in config['Root']['Auto Algorithm Control']:
            exposure_time_lower_limit = config['Root']['Auto Algorithm Control']['Exposure Time Lower Limit']
            if cam.AutoExposureExposureTimeLowerLimit.GetAccessMode() == PySpin.RW:
                cam.AutoExposureExposureTimeLowerLimit.SetValue(exposure_time_lower_limit)
                print('Exposure Time Lower Limit set to %f...' % cam.AutoExposureExposureTimeLowerLimit.GetValue())

        # Set Exposure Time Upper Limit
        # check if exposure time upper limit is in config dictionary
        if 'Exposure Time Upper Limit' in config['Root']['Auto Algorithm Control']:
            exposure_time_upper_limit = config['Root']['Auto Algorithm Control']['Exposure Time Upper Limit']
            if cam.AutoExposureExposureTimeUpperLimit.GetAccessMode() == PySpin.RW:
                cam.AutoExposureExposureTimeUpperLimit.SetValue(exposure_time_upper_limit)
                print('Exposure Time Upper Limit set to %f...' % cam.AutoExposureExposureTimeUpperLimit.GetValue())

        # Set Gain Lower Limit
        # check if gain lower limit is in config dictionary
        if 'Gain Lower Limit' in config['Root']['Auto Algorithm Control']:
            gain_lower_limit = config['Root']['Auto Algorithm Control']['Gain Lower Limit']
            #print("Current Gain Lower Limit: %f" % cam.AutoExposureGainLowerLimit.GetValue())
            if cam.AutoExposureGainLowerLimit.GetAccessMode() == PySpin.RW:
                cam.AutoExposureGainLowerLimit.SetValue(gain_lower_limit)
                print('Gain Lower Limit set to %f...' % cam.AutoExposureGainLowerLimit.GetValue())

        # Set Gain Upper Limit
        # check if gain upper limit is in config dictionary
        if 'Gain Upper Limit' in config['Root']['Auto Algorithm Control']:
            gain_upper_limit = config['Root']['Auto Algorithm Control']['Gain Upper Limit']
            #print("Current Gain Upper Limit: %f" % cam.AutoExposureGainUpperLimit.GetValue())
            if cam.AutoExposureGainUpperLimit.GetAccessMode() == PySpin.RW:
                cam.AutoExposureGainUpperLimit.SetValue(gain_upper_limit)
                print('Gain Upper Limit set to %f...' % cam.AutoExposureGainUpperLimit.GetValue())

        # Set Target Grey Value Lower Limit
        # check if target grey value lower limit is in config dictionary
        if 'Target Grey Value Lower Limit' in config['Root']['Auto Algorithm Control']:
            target_grey_value_lower_limit = config['Root']['Auto Algorithm Control']['Target Grey Value Lower Limit']
            if cam.AutoExposureGreyValueLowerLimit.GetAccessMode() == PySpin.RW:
                cam.AutoExposureGreyValueLowerLimit.SetValue(target_grey_value_lower_limit)
                print('Target Grey Value Lower Limit set to %f...' % cam.AutoExposureGreyValueLowerLimit.GetValue())

        # Set Target Grey Value Upper Limit
        # check if target grey value upper limit is in config dictionary
        if 'Target Grey Value Upper Limit' in config['Root']['Auto Algorithm Control']:
            target_grey_value_upper_limit = config['Root']['Auto Algorithm Control']['Target Grey Value Upper Limit']
            #print("Current Target Grey Value Upper Limit: %f" % cam.AutoExposureGreyValueUpperLimit.GetValue())
            if cam.AutoExposureGreyValueUpperLimit.GetAccessMode() == PySpin.RW:
                cam.AutoExposureGreyValueUpperLimit.SetValue(target_grey_value_upper_limit)
                print('Target Grey Value Upper Limit set to %f...' % cam.AutoExposureGreyValueUpperLimit.GetValue())

        # Set EV Compensation
        # check if EV compensation is in config dictionary
        if 'EV Compensation' in config['Root']['Auto Algorithm Control']:
            ev_compensation = config['Root']['Auto Algorithm Control']['EV Compensation']
            if cam.AutoExposureEVCompensation.GetAccessMode() == PySpin.RW:
                cam.AutoExposureEVCompensation.SetValue(ev_compensation)
                print('EV Compensation set to %f...' % cam.AutoExposureEVCompensation.GetValue())

        # Set Auto Exposure Damping
        # check if auto exposure damping is in config dictionary
        if 'Auto Exposure Damping' in config['Root']['Auto Algorithm Control']:
            auto_exposure_damping = config['Root']['Auto Algorithm Control']['Auto Exposure Damping']
            if cam.AutoExposureControlLoopDamping.GetAccessMode() == PySpin.RW:
                cam.AutoExposureControlLoopDamping.SetValue(auto_exposure_damping)
                print('Auto Exposure Damping set to %f...' % cam.AutoExposureControlLoopDamping.GetValue())

        # Set Auto Exposure Control Priority
        # check if auto exposure control priority is in config dictionary
        if 'Auto Exposure Control Priority' in config['Root']['Auto Algorithm Control']:
            auto_exposure_control_priority = config['Root']['Auto Algorithm Control']['Auto Exposure Control Priority']
            if cam.AutoExposureControlPriority.GetAccessMode() == PySpin.RW:
                if auto_exposure_control_priority == 'Gain':
                    cam.AutoExposureControlPriority.SetValue(PySpin.AutoExposureControlPriority_Gain)
                elif auto_exposure_control_priority == 'ExposureTime':
                    cam.AutoExposureControlPriority.SetValue(PySpin.AutoExposureControlPriority_ExposureTime)
                else:
                    print('Unsupported Auto Exposure Control Priority: %s' % auto_exposure_control_priority)
                print('Auto Exposure Control Priority set to %s...' % cam.AutoExposureControlPriority.GetCurrentEntry().GetSymbolic())


    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result



def run_single_camera(cam):
    """
     This function acts as the body of the example; please see NodeMapInfo_QuickSpin example for more
     in-depth comments on setting up cameras.

     :param cam: Camera to run example on.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """
    try:
        # Initialize camera
        cam.Init()

        # Configure exposure
        if not configure_custom_image_settings(cam):
            return False

        # Deinitialize camera
        cam.DeInit()

        return True

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False


def main():
    """
    Example entry point; please see Enumeration_QuickSpin example for more
    in-depth comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """
    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:
        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Release example on each camera
    for i, cam in enumerate(cam_list):

        print('Running example for camera %d...' % i)

        result &= run_single_camera(cam)
        print('Camera %d example complete... \n' % i)

    # Release reference to camera
    # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
    # cleaned up when going out of scope.
    # The usage of del is preferred to assigning the variable to None.
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    return result


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
