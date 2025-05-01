# 关于加载dll

在Python中，通过ctypes可以加载dll，存在两种不同的dll:
- stdcall调用约定：两种加载方式 ：Objdll = ctypes.windll.LoadLibrary("dllpath")和Objdll = ctypes.WinDLL("dllpath")
- cdecl调用约定：也有两种加载方式：Objdll = ctypes.cdll.LoadLibrary("dllpath")和Objdll = ctypes.CDLL("dllpath")

而本项目中，FMI（Functional Mock-up Interface）标准 明确规定接口函数使用 C语言兼容的调用约定（即 cdecl），以确保跨平台和编译器的兼容性。在 FMI 2.0 规范中，所有导出函数（如 fmi2GetReal、fmi2SetReal 等）均需通过 C 语言函数指针访问，且默认遵循 cdecl 约定。

标准明确要求实现者使用 cdecl，因为：
- 跨平台支持：cdecl 是 C 语言的默认约定，广泛适用于 Windows/Linux/macOS。
- 可变参数支持：某些函数可能需要处理可变参数（如日志回调），而 cdecl 是唯一支持可变参数的约定。