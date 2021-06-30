![PyEcog](https://raw.githubusercontent.com/KullmannLab/pyecog2/master/pyecog2/icons/banner_small.png)
# Pyecog2
Under construction.

PyEcog2 is a python software package aimed at exploring, visualizing and analysing (video) EEG telemetry data

## Installation instructions

For alpha testing:
- clone the repository to your local machine
- create a dedicated python 3.8 environment for pyecog2 (e.g. a [conda](https://www.anaconda.com/products/individual) environment)
```shell
conda create --name pyecog2 python=3.8 
```
- activate the environment with `activate pyecog2` in Windows or `source activate pyecog2` in MacOS/Linux
- run the setup script with install option:
```shell
python setup.py install
```
On Windows, if PySide2 fails to load with the following error:
```
ImportError(shiboken2 + ' does not exist')
```
- Run this command:
``` shell
pip install PySide2==5.15.2 --force-reinstall
```

Hopefully in the future:
```shell
pip install pyecog2
```
