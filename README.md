# Scintillometry Tools

Compute heat fluxes & 2D flux footprints from the BLS450 scintillometer.

This repository is a complete rewrite of gampnico/ss19-feldkurs. If you have any existing forks or local clones, **please delete them**. The legacy code no longer works. No user features will be lost, but rewriting may take some time. Contributions are always welcome.

# Processing Scintillometry Data in Complex Terrain

This project initially formed part of a scintillometry field course. Due to licensing constraints, some dependencies are not satisfied by this repository alone. These are indicated below. If you have contributed to any of the code here and would like it removed, please contact me directly or open an issue.

## 1. Features (Roadmap)

### 1.1 Scintillometry

- Parses scintillometry data from BLS450 scintillometer.
- Processes this data and computes sensible heat fluxes.
- Processes topographical data.
- Processes InnFlux and HATPRO data.
- Produces plots of scintillometer data, path topography, and weather data.

### 1.2 Footprint Climatology 

- Processes 2D flux footprints generated by Natascha Kljun's online model, available [here](http://footprint.kljun.net/).
- Makes individual topographical adjustments and stitches footprints together.
- Overlays stitched footprints onto map.

## 2. Workflow

Not all data and dependences are available in this repository, and some of the scripts must be tailored to each individual project, notably topography, station parameters and the times when the boundary layer switches from stable to unstable regimes.

If you are using the scintillometer in Austria, use [DGM 5m data](https://www.data.gv.at/katalog/dataset/digitales-gelandemodell-des-landes-salzburg-5m) to generate topographical data for the scintillometer's path coordinates. Then generate the path transects, which are also necessary for calibrating the scintillometer.

If you are not using the scintillometer in Austria, you will need to find and parse topographical data yourself.

**Scintillometer path coordinates must be accurate. Incorrectly generated topographical data leads to poor calibration and nonsense results!**

# Acknowledgements

This project would not be possible without the invaluable contributions from Josef Zink, Dr. Manuela Lehner, and Dr. Helen Ward.
