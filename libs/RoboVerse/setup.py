# Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the CC BY-NC 4.0 license [see LICENSE for details].

import importlib.util
import os
import shutil
import subprocess
import sys

from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

try:
    from setuptools.command.editable_wheel import editable_wheel

    HAS_EDITABLE_WHEEL = True
except ImportError:
    HAS_EDITABLE_WHEEL = False
    editable_wheel = None

requirements = [
    "black==23.3.0",
    "flake8==7.1.0",
    "isort==5.12.0",
    "yacs==0.1.8",
    "h5py",
    "gym",
    "trimesh",
    "meshcat",
    "scipy",
    "opencv-python-headless",
    "imageio",
    "imageio-ffmpeg==0.4.7",
    "pre-commit",  # Make sure pre-commit is included as a dependency
    "zarr",
    "matplotlib",
    # torch, torchvision, and transformers are installed with specific versions in post-install tasks
]

# --- Optional Requirements ---
# Define different sets of optional dependencies
# Users can install these using pip install -e ".[extra_name]"
extras_require = {
    # 'lerobot': Dependencies for LeRobot functionality
    "lerobot": [
        # The upstream lerobot wheel currently declares a huggingface-hub>=1.0
        # requirement, which conflicts with the transformers 4.x stack used by VLA-0.
        # We install the package itself in post-install with --no-deps after the
        # shared runtime dependencies have already been resolved by the main env.
    ],
}

# Create an 'all' extra that automatically includes all optional dependencies
all_extras = []
for extra_deps in extras_require.values():
    all_extras.extend(extra_deps)
# Use set to remove duplicates if a package is in multiple extras
extras_require["all"] = list(set(all_extras))

# At the top, after imports
print(f"Environment: PIP_REQ_EXTRAS={os.environ.get('PIP_REQ_EXTRAS', 'not set')}")


def _ensure_pip_available():
    """Bootstrap pip inside uv-created virtualenvs that start without it."""
    if importlib.util.find_spec("pip") is None:
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError(
                "pip is unavailable in the current environment and uv was not found on PATH."
            )
        subprocess.check_call([uv, "pip", "install", "--python", sys.executable, "pip"])


# --- Shared Post-Install Tasks ---
# This function is called by CustomInstallCommand, CustomDevelopCommand, and CustomEditableWheelCommand
def _run_post_install_tasks():
    """
    Shared installation logic for all custom install commands.

    Handles:
    - Installing pre-commit hooks (if available)
    - Installing optional extras based on PIP_REQ_EXTRAS environment variable
    - Verifying lerobot system dependencies
    """
    print("\n" + "=" * 80)
    print("Running custom post-install tasks...")
    print("=" * 80 + "\n")
    _ensure_pip_available()

    # Try to install pre-commit hooks (may not be available during wheel build)
    try:
        subprocess.check_call(["pre-commit", "install"])
        print("✓ pre-commit hooks installed")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"⚠ Skipping pre-commit install (not available yet): {e}")
        print(
            "  You can manually run 'pre-commit install' after installation completes."
        )

    # Use environment variable approach for extras
    requested_extras = []

    # Check environment variable
    if os.environ.get("PIP_REQ_EXTRAS"):
        extras = os.environ.get("PIP_REQ_EXTRAS").split(",")
        requested_extras.extend(extras)
        print(
            f"Found PIP_REQ_EXTRAS environment variable: {os.environ.get('PIP_REQ_EXTRAS')}"
        )
    else:
        print("PIP_REQ_EXTRAS environment variable not found")

    # Debug info
    print(f"Debug: sys.argv = {sys.argv}")
    print(f"Debug: cwd = {os.getcwd()}")
    print(f"Debug: __dir__ = {os.path.dirname(os.path.abspath(__file__))}")
    print(f"Requested extras: {list(set(requested_extras))}")  # Deduplicate

    # Check if 'lerobot' or 'all' extras were requested
    if "lerobot" in requested_extras or "all" in requested_extras:
        print("\n" + "-" * 80)
        print("Installing lerobot extras...")
        print("-" * 80 + "\n")

        print("Installing lerobot==0.5.1 without transitive dependency resolution...")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-v",
                "--no-deps",
                "lerobot==0.5.1",
            ]
        )
        if shutil.which("ffmpeg") is None:
            print(
                "WARNING: ffmpeg was not found on PATH. "
                "LeRobot dataset video loading may fail until ffmpeg is installed."
            )

    print("\n" + "=" * 80)
    print("Custom post-install tasks completed!")
    print("=" * 80 + "\n")


# --- Custom Install Commands ---
# These commands hook into pip's installation process to run custom post-install tasks


class CustomInstallCommand(install):
    """Custom installation command to run pre-commit install and handle local dependencies"""

    def run(self):
        install.run(self)
        _run_post_install_tasks()


class CustomDevelopCommand(develop):
    """Custom develop command to handle local dependencies for development mode"""

    def run(self):
        develop.run(self)
        _run_post_install_tasks()


if HAS_EDITABLE_WHEEL:

    class CustomEditableWheelCommand(editable_wheel):
        """Custom editable_wheel command for modern pip (PEP 660)"""

        def run(self):
            editable_wheel.run(self)
            _run_post_install_tasks()


# Set up command class dictionary
cmdclass_dict = {
    "install": CustomInstallCommand,
    "develop": CustomDevelopCommand,
}

# Add editable_wheel command if available (for modern pip versions)
if HAS_EDITABLE_WHEEL:
    cmdclass_dict["editable_wheel"] = CustomEditableWheelCommand

setup(
    name="roboverse",
    packages=find_packages(),
    install_requires=requirements,
    extras_require=extras_require,
    cmdclass=cmdclass_dict,
)
