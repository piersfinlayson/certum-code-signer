# Certum Code Signer

A containerised web server for signing Windows executables using a Certum supplied code signing certificate (including an Open Source Developer certicate), stored on a smartcard.

It is particularly useful if you are building Windows software on non x86_64 Windows or other platforms where you cannot easily use the standard Windows code signing tools.

It can be used like so:

```bash
curl --fail-with-body -F "file=@path/to/your/file.exe" http://server-ip:8000/sign -o signed-file.exe
```

## Prerequisites

[Docker](https://docs.docker.com/get-started/get-docker/)

A smart card reader and smart card, with a code signing certificate already installed.

Export the code signing certificate from the smart card to a `cert.pem` file, or download it from Certum's website.  This must include the intermediate and root certificates.  These should be concatenated together in a single file like so:

```
-----BEGIN CERTIFICATE-----
[Your code signing certificate]
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[Intermediate certificate]
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[Root certificate]
-----END CERTIFICATE-----
```

## Setup

Create a .env file using sample.env as a template and fill in the required values.  DO NOT store your PIN in `sample.env` - only in a file called `.env`.

Copy the `cert.pem` file for your certificate (including the intermediate and root certificates) into the project root directory.

Modify `start.sh` if you wish to expose the server on a different port (8000 is used by default).

## Build and Run

```bash
./start.sh
```

## Usage

Send a POST request to `http://server-ip:8000/sign` with the file to be signed as form data.  The signed file will be returned in the response.

Examples follow.

### Curl

```bash
curl --fail-with-body -F "file=@path/to/your/file.exe" http://server-ip:8000/sign -o signed-file.exe
```

### Python

```python
import requests
url = "http://server-ip:8000/sign"
files = {'file': open('path/to/your/file.exe', 'rb')}
response = requests.post(url, files=files)
if response.status_code == 200:
    open('signed-file.exe', 'wb').write(response.content)
    print("Signing successful")
else:
    print(f"Error {response.status_code}: {response.text}")
```

### Windows PowerShell

```powershell
$FilePath = "path\to\your\file.exe"
$Url = "http://server-ip:8000/sign"
$SignedFilePath = "signed-file.exe"

try {
    # Resolve to absolute path
    $FilePath = Resolve-Path $FilePath
    
    # Create multipart form data
    $FileContent = [System.IO.File]::ReadAllBytes($FilePath)
    $Boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    
    $BodyLines = @(
        "--$Boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$(Split-Path $FilePath -Leaf)`"",
        "Content-Type: application/octet-stream$LF",
        [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($FileContent),
        "--$Boundary--$LF"
    ) -join $LF
    
    # Upload and download signed file
    $Response = Invoke-WebRequest -Uri $Url -Method Post -ContentType "multipart/form-data; boundary=$Boundary" -Body $BodyLines -UseBasicParsing
    [System.IO.File]::WriteAllBytes($SignedFilePath, $Response.Content)
    
    Write-Host "Signing successful: $SignedFilePath"
} catch {
    Write-Host "Signing failed: $_"
    exit 1
}
```