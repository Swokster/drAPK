## Development Environment Setup
This project requires JDK 17 for building and running.

### Installing JDK 17
We use the build from Eclipse Adoptium (formerly AdoptOpenJDK).

⚠️Important: This project is configured to use a portable JDK version located in the project directory.

Download JDK 17 (Portable Version):

Version: jdk-17.0.16+8

https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.16%2B8/OpenJDK17U-jdk_x64_windows_hotspot_17.0.16_8.zip

### Setup Instructions:

Create a utils folder in the root directory of this project

Extract the downloaded portable JDK archive into the utils folder in the root directory


### Configuration:

The project is already configured to look for Java in utils/jdk-17.0.16+8/bin/java.exe (Windows)