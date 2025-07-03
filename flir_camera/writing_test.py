import numpy as np
import time
import os

# Parameters
filename = "/mnt/ssd/test_write_speed.npy"
matrix_shape = (10000, 10000)  # Adjust size as needed

# Generate random matrix
matrix = np.random.rand(*matrix_shape)

# Measure write speed
start_time = time.time()
np.save(filename, matrix)
end_time = time.time()

file_size_mb = (matrix.nbytes) / (1024 * 1024)
write_time = end_time - start_time
speed_mb_s = file_size_mb / write_time

print(f"Matrix shape: {matrix_shape}")
print(f"File size: {file_size_mb:.2f} MB")
print(f"Write time in micro sd card: {write_time:.4f} seconds")
print(f"Write speed in micro sd card: {speed_mb_s:.2f} MB/s")

# delete the file after testing
os.remove(filename)

# Parameters
filename = "test_write_speed.npy"
# Measure write speed
start_time = time.time()
np.save(filename, matrix)
end_time = time.time()

write_time = end_time - start_time
speed_mb_s = file_size_mb / write_time
print(f"Write time in ssd: {write_time:.4f} seconds")
print(f"Write speed in ssd: {speed_mb_s:.2f} MB/s")
os.remove(filename)