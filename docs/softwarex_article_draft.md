# Draft SoftwareX article text

## Title

WaveLab Studio: A research software tool for two-dimensional wave-propagation experiments in heterogeneous scenes

## Highlights

- Interactive Python software for constructing two-dimensional heterogeneous wave-propagation scenes.
- YAML-based workflow for defining sources, material objects, and simulation parameters.
- Lightweight solver pipeline producing reference, approximated, and error-map field visualisations.
- Export of numerical arrays, scalar metrics, static figures, and optional wave-propagation animations.
- Designed for teaching, prototyping, and exploratory AI/PINN-oriented electromagnetic simulation workflows.

## Motivation and significance

Electromagnetic and wave-propagation simulations are important in wireless communication, radar analysis, indoor propagation studies, and engineering education. Traditional numerical approaches such as the finite-difference time-domain method and the finite element method are well established, but they often require dedicated modelling tools, careful discretisation, and substantial computational resources for large or heterogeneous scenes. At the same time, physics-informed machine-learning methods have created interest in alternative workflows where physical constraints, neural approximators, and interactive experimentation can be combined.

WaveLab Studio was developed to support rapid construction, execution, and visual analysis of simplified two-dimensional wave-propagation scenarios. The software allows users to define a signal source, add multiple material objects, configure material-dependent attenuation and transmission properties, execute a lightweight solver, and inspect predicted, reference, and error-map field outputs. The tool is intended as a research and teaching prototype rather than a replacement for validated electromagnetic solvers. Its main contribution is an integrated workflow that connects scene definition, simulation execution, visualisation, animation, and result archiving in a single Python environment.

## Software description

WaveLab Studio is implemented in Python and consists of a graphical scene builder, command-line scene utilities, a solver script, and visualisation utilities. Scenes are represented using YAML files containing material definitions, signal-source parameters, and a list of scene objects. Objects can represent simple geometric obstacles or material regions such as circles, rectangles, and triangles. Each material is associated with attenuation, reflection, transmission, and scattering parameters used by the simulation pipeline.

The desktop interface is implemented using Tkinter and provides controls for editing the scene, running the solver, opening generated results, previewing animations, and saving selected generations. The solver pipeline creates scalar wave-field outputs on a two-dimensional grid. It produces a reference or target field, an approximated or predicted field, and an absolute error map. These outputs are exported as both image files and NumPy arrays, allowing subsequent quantitative or visual analysis.

The software also includes an optional animation renderer for producing GIF-based previews of wave propagation. A command-line scene editor can list and modify objects and materials in the YAML scene file, which enables scripted workflows and lightweight testing without launching the GUI.

## Illustrative example

A typical workflow starts by defining a YAML scene with a source location, signal frequency, amplitude, and several material objects. The user can run a low-resolution simulation from the command line and generate output images for the target field, approximated field, and error map. The same scene can be opened in the graphical interface for interactive editing and visual inspection.

```bash
python solver_simple_torch.py examples/basic_scene.yaml \
  --epochs 100 \
  --nx 96 \
  --ny 64 \
  --steps 8 \
  --no_animation \
  --out_dir results/basic_scene
```

The resulting output directory contains field visualisations, numerical arrays, and a metrics file documenting the main settings and scalar errors. This makes the example reproducible and suitable for demonstrations, teaching, or regression testing.

## Impact

WaveLab Studio lowers the barrier for experimenting with heterogeneous wave-propagation scenes and AI-oriented simulation workflows. The tool can be used by students and researchers who need a lightweight environment for testing scene configurations, generating visual examples, or preparing datasets and demonstrations for more advanced solvers. Its YAML-based input format and scriptable solver make it suitable for reproducible examples, while the graphical interface supports interactive exploration and teaching.

The software is particularly useful as a prototyping layer around future physics-informed neural network implementations. Although the current solver should be treated as a simplified scalar approximation, the software architecture separates scene definition, solver execution, visualisation, and result export, which allows the solver backend to be extended or replaced in future versions.

## Limitations and future work

The current implementation is a research prototype and should not be interpreted as a validated full-vector Maxwell-equation solver. The main solver uses a simplified scalar-field approximation with heuristic material effects and visual smoothing. Quantitative claims about electromagnetic accuracy therefore require additional validation against analytical cases or established numerical solvers such as FDTD or FEM.

Future work will focus on unifying the scene schema, improving automated tests, separating the GUI and solver into a package structure, and adding validated benchmark examples. Further development may also include a fully documented physics-informed neural-network backend, adaptive sampling, additional material models, and systematic comparison against reference numerical simulations.

## Conclusions

WaveLab Studio provides an integrated Python workflow for constructing, running, and visualising simplified two-dimensional wave-propagation experiments in heterogeneous scenes. By combining a graphical scene editor, YAML-based configuration, solver execution, result export, and animation tools, it supports teaching, prototyping, and exploratory research in AI/PINN-oriented electromagnetic simulation workflows. The software is suitable for publication as a research software artefact after repository clean-up, documentation, licensing, and release archiving.
