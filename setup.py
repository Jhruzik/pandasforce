import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pandasforce",
    version="0.0.10",
    author="Joshua Hruzik",
    author_email="joshua.hruzik@gmail.com",
    description="Integration of SalesForce and Pandas",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jhruzik/pandasforce",
    packages=setuptools.find_packages(),
    install_requires=["requests", "pandas"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
	"Intended Audience :: Developers",
	"Topic :: Database",
	"Topic :: Office/Business"
	
    ],
    python_requires='>=3.6',
)

