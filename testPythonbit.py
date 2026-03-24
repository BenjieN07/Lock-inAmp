import ctypes
print(ctypes.sizeof(ctypes.c_voidp))  # 4 for 32-bit python, 8 for 64-bit python
# 32-bit python is needed for compatibility with older versions of DLL, for example the OpusCMD334.dll for Bruker
