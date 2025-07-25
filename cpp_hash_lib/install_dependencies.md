# Windows 环境依赖安装指南

本指南将帮助您在Windows环境下安装编译C++哈希库所需的依赖。

## 必需依赖

### 1. CMake 安装

#### 方法一：官方安装包（推荐）
1. 访问 [CMake官网](https://cmake.org/download/)
2. 下载 "Windows x64 Installer" (cmake-x.x.x-windows-x86_64.msi)
3. 运行安装包，**重要：勾选 "Add CMake to the system PATH"**
4. 完成安装后重启命令行

#### 方法二：使用Chocolatey
```powershell
# 以管理员身份运行PowerShell
choco install cmake
```

#### 方法三：使用winget
```powershell
winget install Kitware.CMake
```

### 2. C++ 编译器安装

#### 方法一：Visual Studio Build Tools（推荐）
1. 访问 [Visual Studio下载页面](https://visualstudio.microsoft.com/zh-hans/downloads/)
2. 下载 "Visual Studio 2022 生成工具" (Build Tools)
3. 运行安装程序，选择以下组件：
   - **C++ 生成工具**
   - **Windows 10/11 SDK**
   - **MSVC v143 编译器工具集**
4. 完成安装

#### 方法二：完整Visual Studio Community
1. 下载 [Visual Studio Community 2022](https://visualstudio.microsoft.com/zh-hans/vs/community/)
2. 安装时选择 "使用C++的桌面开发" 工作负载
3. 确保包含 MSVC 编译器和 Windows SDK

#### 方法三：MinGW-w64（轻量级选择）
```powershell
# 使用MSYS2安装MinGW
# 1. 下载并安装 MSYS2: https://www.msys2.org/
# 2. 在MSYS2终端中运行：
pacman -S mingw-w64-x86_64-gcc
pacman -S mingw-w64-x86_64-cmake

# 3. 将 C:\msys64\mingw64\bin 添加到系统PATH
```

## 验证安装

安装完成后，打开新的PowerShell窗口并运行以下命令验证：

```powershell
# 检查CMake
cmake --version

# 检查编译器（根据安装的编译器选择其一）
# Visual Studio (cl)
cl

# MinGW (gcc)
gcc --version

# Git（通常已安装）
git --version
```

## 可选：安装vcpkg包管理器

vcpkg可以简化OpenCV和OpenSSL的安装：

```powershell
# 克隆vcpkg
git clone https://github.com/Microsoft/vcpkg.git C:\vcpkg
cd C:\vcpkg

# 构建vcpkg
.\bootstrap-vcpkg.bat

# 安装依赖包
.\vcpkg.exe install opencv4:x64-windows openssl:x64-windows

# 设置环境变量（可选）
[Environment]::SetEnvironmentVariable("VCPKG_ROOT", "C:\vcpkg", "User")
```

## 常见问题解决

### 问题1：CMake未找到
**解决方案**：
- 确保安装时勾选了 "Add to PATH"
- 手动添加CMake到系统PATH：`C:\Program Files\CMake\bin`
- 重启命令行或重启计算机

### 问题2：编译器未找到
**解决方案**：
- 确保安装了正确的Visual Studio组件
- 使用 "Developer Command Prompt for VS 2022" 而不是普通命令行
- 或者安装MinGW并添加到PATH

### 问题3：权限问题
**解决方案**：
- 以管理员身份运行安装程序
- 确保有足够的磁盘空间（至少5GB）

## 安装完成后

依赖安装完成后，返回项目目录并重新运行构建脚本：

```powershell
cd E:\code\Python\xImageDuplicateChecker\cpp_hash_lib
python build.py
```

## 快速安装脚本

如果您有管理员权限，可以使用以下PowerShell脚本快速安装：

```powershell
# 以管理员身份运行PowerShell，然后执行：

# 安装Chocolatey（如果未安装）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装依赖
choco install cmake visualstudio2022buildtools -y

# 重启PowerShell后验证
cmake --version
cl
```

---

**注意**：安装完成后请重启命令行窗口，以确保环境变量生效。