from setuptools import setup, find_packages

setup(
    name="vibegit-mcp",
    version="0.1.1",
    author="VibeGit Team",
    author_email="team@vibegit.com",
    description="VibeGit MCP server for AI conversation logging and analysis",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/vibegit/vibegit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10", 
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Chat"
    ],
    keywords="mcp ai conversation logging assistant",
    python_requires=">=3.9",
    install_requires=[
        "mcp>=1.14.0",
        "anyio>=4.5.0"
    ],
    entry_points={
        "console_scripts": [
            "vibegit-mcp=vibegit.server:main",
        ],
    },
    license="MIT",
    include_package_data=True,
)