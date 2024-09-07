# OWASP-Security-Header-Checker-Tool
![image](https://github.com/user-attachments/assets/4f3b5b19-798a-4b7d-b9c5-f64c41de0252)

The OWASP Security Header Checker Tool is a user-friendly application designed to help developers and security professionals assess the security headers of web applications. This tool fetches and evaluates the HTTP response headers of a specified URL against a list of recommended security headers from OWASP (Open Web Application Security Project). By using this tool, users can identify missing security headers and enhance the security posture of their web applications. This tool utilizes the requests, BeautifulSoup, and Tkinter libraries for its functionality.  

[Download Latest Version](https://github.com/javelinsoft/OWASP-Security-Header-Checker-Tool/releases/download/v1.0.0/Check.exe)

## Features

* Fetch Latest OWASP Headers: Automatically retrieves the latest recommended security headers from the OWASP website.  
* Crawl Links: Checks the headers of links found on the specified webpage, ensuring comprehensive coverage.  
* User-Friendly Interface: Built with Tkinter, the tool provides an intuitive GUI for easy interaction.  
* Clipboard Functionality: Easily copy URLs, header names, and statuses to the clipboard for convenience.  
* Stop Functionality: Users can halt the crawling process at any time.  

## Installation

* Download the latest release of Check.exe from the Releases section.  
* Ensure you have the necessary permissions to run executable files on your system.

## Usage

* Launch the application by double-clicking Check.exe.  
* Enter the target URL in the provided field.  
* Specify the crawl time in seconds.  
* Click the "Check Headers" button to start the process.  
* Review the results displayed in the table, which shows the tested URL, header names, and their statuses.  
* Use the right-click context menu to copy information to your clipboard as needed.  
* Click the "Stop Check" button to halt the process at any time.  

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, please open an issue or submit a pull request.

