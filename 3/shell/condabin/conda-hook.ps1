$Env:CONDA_EXE = "/home/runner/work/shef-ai.github.io/shef-ai.github.io/3/bin/conda"
$Env:_CONDA_EXE = "/home/runner/work/shef-ai.github.io/shef-ai.github.io/3/bin/conda"
$Env:_CE_M = $null
$Env:_CE_CONDA = $null
$Env:CONDA_PYTHON_EXE = "/home/runner/work/shef-ai.github.io/shef-ai.github.io/3/bin/python"
$Env:_CONDA_ROOT = "/home/runner/work/shef-ai.github.io/shef-ai.github.io/3"
$CondaModuleArgs = @{ChangePs1 = $False}

Import-Module "$Env:_CONDA_ROOT\shell\condabin\Conda.psm1" -ArgumentList $CondaModuleArgs

Remove-Variable CondaModuleArgs