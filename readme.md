add this to the .vscode/settings.json to have proper linting
```
{
    "python.autoComplete.extraPaths": ["./TLKCore/lib"]
}
```

DEV LOG
* added .pyi interface for service
* added tymtek_wrapper.py to keep an abstract class of the tymtek devices
* added csi_beamscan.py to interface with gnuradio and capture a simple beamscan (uses: gnu_manager.py and trans.py)
* added csi_beamscan_vis.py and csi_beamscan_vis_gp.py to visualize the data
* init git, the /files folder with all the calibration files is ignored from git and will need to be locally added!