
# MacVacuum

MacVacuum is a powerful disk space optimization tool for macOS primarily, to help you get rid of the skeletons in your closet (or rather your machine)
## Features

- **Quick Scan**: Rapidly checks common locations for large files and unnecessary items.
- **Deep Scan**: Thoroughly examines the entire system for space-consuming files.
- **Custom Scan**: Allows users to select specific directories for targeted cleaning.
- **System Information**: Provides real-time updates on CPU usage, memory utilization, and hardware details.
- **Disk Usage**: Displays comprehensive information about disk partitions and their usage.
- **User-Friendly Interface**: Intuitive GUI with sortable results and progress tracking.

## Installation

1. Ensure you have Python 3.x installed on your macOS system.
2. Clone this repository or download the source code.
3. Install the required dependencies:


pip install send2trash psutil


## Usage

Run the application by executing:


python macvacuum.py


## Tabs

1. **Scan**: Initiate scans and view results.
2. **System**: Monitor real-time system information.
3. **Disk**: Check disk usage across partitions.
4. **Help**: Access quick usage instructions.

## Caution

Exercise care when using the cleaning features, as deleted files are moved to the Trash and can be permanently removed.

## Dependencies

- tkinter
- send2trash
- psutil

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
