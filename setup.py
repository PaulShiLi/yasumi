from setuptools import setup, find_packages
import sys

extras = {}
if sys.platform == "darwin":
    extras["mac"] = ["pyobjc-framework-Quartz>=7.3"]  # Quartz via PyObjC for macOS
if sys.platform == "win32":
    extras["win"] = ["windows-curses>=2.4.1"]

setup(
    name="Yasumi",
    version="0.1.0",
    description="A cross-platform AFK image clicker with macro recording and playback",
    author="Paul Li",
    author_email="paul.shi.li.05@gmail.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "opencv-contrib-python==4.11.0.86",
        "pyautogui==0.9.54",
        "pydirectinput-rgx",
        "pynput==1.8.0",
        "scikit-image==0.25.2",
        "numpy",
        "keyboard==0.13.5"
    ],
    extras_require=extras,
    entry_points={
        "console_scripts": [
            "yasumi = yasumi:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
