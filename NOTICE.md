# MD Viewer Pro — Third-Party Notices

This application uses the following open-source libraries.
Their license texts are reproduced below as required by each license.

---

## Qt / PySide6 / shiboken6

**License**: GNU Lesser General Public License v3.0 (LGPL-3.0-only)  
**Copyright**: © 2024 The Qt Company Ltd. and contributors  
**Source**: https://code.qt.io/cgit/pyside/pyside-setup.git/

This application uses PySide6 (the official Python bindings for Qt 6)
under the terms of the **GNU Lesser General Public License version 3 (LGPL-3.0)**.

Under the LGPL-3.0, you are permitted to:
- Use this application for any purpose
- Distribute this application

You are also entitled to:
- Obtain the corresponding machine-readable source of PySide6 from the URL above
- Modify PySide6 and rebuild this application using the provided `main.py` and
  `MDViewerPro.spec` (PyInstaller spec file), which allow relinking with a
  modified version of PySide6

The full text of the LGPL-3.0 is available at:  
https://www.gnu.org/licenses/lgpl-3.0.html

---

## Python-Markdown

**License**: BSD 3-Clause License  
**Copyright**: © 2007, 2008 The Python Markdown Project; © 2004–2006 Yuri Takhteyev; © 2004 Manfred Stienstra

```
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## Pygments

**License**: BSD 2-Clause License  
**Copyright**: © 2006–2022 by the respective authors (see Pygments AUTHORS file)

```
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## PyObjC (pyobjc-core, pyobjc-framework-Cocoa)

**License**: MIT License  
**Copyright**: © 2002–2003 Bill Bumgarner, Ronald Oussoren, Steve Majewski, Lele Gaifax, et al.; © 2003–2025 Ronald Oussoren

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

---

## PyInstaller (build tool only — not shipped)

**License**: GPL v2 or later with Bootloader Exception  
**Note**: PyInstaller is used **only as a build tool** and is **not distributed**
as part of MD Viewer Pro. The PyInstaller bootloader embedded in the application
is covered by the Bootloader Exception, which explicitly permits distribution
in non-GPL applications:

> "In addition to the permissions in the GNU General Public License, the authors
> give you unlimited permission to link or embed compiled bootloader and related
> files into combinations with other programs, and to distribute those combinations
> without any restriction coming from the use of those files."

---

## Python Standard Library

**License**: Python Software Foundation License (PSF-2.0)  
**Source**: https://docs.python.org/3/license.html

---

## LGPL Relinking Notice

In compliance with LGPL-3.0 §4, this application can be rebuilt with a
different version of PySide6/Qt by:

1. Obtaining the application source: `main.py` (included in the repository)
2. Obtaining the build specification: `MDViewerPro.spec` (included in the repository)
3. Installing a different version of PySide6 in the virtual environment
4. Running `./build_dmg.sh`

Repository: `/Users/yuki/Used_ai/MD Viewer Pro/`
