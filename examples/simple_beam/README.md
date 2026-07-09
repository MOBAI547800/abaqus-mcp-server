# Simple Cantilever Beam Example

This example runs a linear elastic cantilever beam analysis through the Abaqus MCP Server.

## Model

- Beam: 5×1×1 mm, 2 C3D8 elements
- Material: Steel (E=210,000 MPa, ν=0.3)
- Fixed at one end, 600 N downward tip load

## Usage with Claude Code

Ask Claude Code:

1. "Validate the workspace for Abaqus"
2. "Submit the beam.inp file from examples/simple_beam/"
3. "Check the job status"
4. "Read the job logs to see if it completed"
5. "Extract the ODB summary"
6. "Extract the maximum Mises stress"
7. "Extract the tip displacement history"

## Direct Abaqus Commands

```bash
# Submit manually
cd examples/simple_beam
abaqus job=beam input=beam.inp interactive

# Check results
abaqus python -c "from odbAccess import openOdb; odb=openOdb('beam.odb'); print(list(odb.steps.keys())); odb.close()"
```
