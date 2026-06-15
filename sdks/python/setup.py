"""
bolt_prediction_sdk 安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="bolt_prediction_sdk",
    version="1.0.0",
    description="螺栓预紧力预测系统 Python SDK",
    author="SDK Generator",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=["httpx>=0.26.0", "pydantic>=2.0.0", "tenacity>=8.2.0"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
