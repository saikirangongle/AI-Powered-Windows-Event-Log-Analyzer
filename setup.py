from setuptools import setup, find_packages

setup(
    name="win-log-interpreter",
    version="0.1.0",
    description="AI-powered Windows Event Log Interpreter (Gemini-Only Edition)",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.10",

    install_requires=[
        "requests>=2.32.5",
        "jsonschema>=4.21.1",
        "python-dotenv>=1.2.1",
        "pillow>=12.0.0",
    ],

    extras_require={
        "dev": [
            "pytest>=9.0.1",
            "pytest-cov>=7.0.0",
            "flake8>=7.3.0",
            "black>=25.11.0",
        ]
    },

    entry_points={
        "console_scripts": [
            "winlog=main.app:main",
        ]
    },

    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: System :: Logging",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
