# Certum Code Signer

A containerised web server for signing Windows executables using a Certum supplied code signing certificate (including an Open Source Developer certicate), stored on a smartcard.

It is particularly useful if you are building Windows software on non x86_64 Windows or other platforms where you cannot easily use the standard Windows code signing tools.

For security, it forces
- the PIN to be held separately from the signing server and passed in with each signing request
- HTTPS for all connections to the signing server, to protect the PIN in transit.

DO NOT STORE THE PIN ON THE SIGNING SERVER.  THIS DEFEATS THE POINT OF USING A SMART CARD.

It can be used like so:

```bash
curl \
  --fail-with-body \
  -F "file=@path/to/your/file.exe" \
  -F "pin=SMARTCARD_PIN" \
  https://server-ip:8443/sign \
  -k \
  -o signed-file.exe
```

Note that here `-k` is used to skip verification of the server's HTTPS certificate.  In production you should use `--cacert https_cert.pem` instead, where `https_cert.pem` is the self-signed certificate you created for the server.  See below.

## Prerequisites

[Docker](https://docs.docker.com/get-started/get-docker/)

A smart card reader and smart card, with a code signing certificate already installed.

Export the code signing certificate from the smart card to a `signing_cert.pem` file, or download it from Certum's website.  This must include the intermediate and root certificates.  These should be concatenated together in a single file like so:

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

Copy the `signing_cert.pem` file for your certificate (including the intermediate and root certificates) into the project root directory.

Modify `start.sh` if you wish to expose the server on a different port (8443 is used by default).

Set up an HTTPS certificate for the server:

```bash
# Generate self-signed cert (10 year validity)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout https_key.pem -out https_cert.pem -days 3650 \
  -subj "/CN=certum-code-signer.local" \
  -addext "subjectAltName=DNS:certum-code-signer.local"
```

You can add additional DNS and IP entries to the `subjectAltName` as required, based on how the server may be addressed, as follows:

```
  -addext "subjectAltName=DNS:certum-code-signer.local,DNS:other-name.local,IP:1.2.3.4
```

Export `https_cert.pem` to any clients that will connect to the server, and import as trusted, either globally, or for the duration of the signing operation - see examples below.

## Build and Run

```bash
./start.sh
```

## Usage

Send a POST request to `http://server-ip:8443/sign` with the file to be signed as form data, and the PIN as a separate form field.  The signed file will be returned in the response.

Examples follow.

### Curl

```bash
curl --fail-with-body \
  -F "file=@path/to/your/file.exe" \
  -F "pin=SMARTCARD_PIN" \
  https://server-ip:8443/sign \
  --cacert https_cert.pem \
  -o signed-file.exe
```

### Python

(Untested - may be bugs)

```python
import requests
url = "https://server-ip:8443/sign"
files = {'file': open('path/to/your/file.exe', 'rb')}
data = {'pin': 'SMARTCARD_PIN'}
response = requests.post(url, files=files, data=data, verify='https_cert.pem')
if response.status_code == 200:
    open('signed-file.exe', 'wb').write(response.content)
    print("Signing successful")
else:
    print(f"Error {response.status_code}: {response.text}")
```

### Windows PowerShell

(Untested - may be bugs)

```powershell
$FilePath = "path\to\your\file.exe"
$Url = "http://server-ip:8443/sign"
$SignedFilePath = "signed-file.exe"
$Pin = "SMARTCARD_PIN"
$CertPath = "path\to\https_cert.pem"

# Load the certificate
$Cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertPath)

# Add cert to trusted root store for this session
$Store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
$Store.Open("ReadWrite")
$Store.Add($Cert)
$Store.Close()

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
        "--$Boundary",
        "Content-Disposition: form-data; name=`"pin`"$LF",
        $Pin,
        "--$Boundary--$LF"
    ) -join $LF
    
    # Upload and download signed file
    $Response = Invoke-WebRequest -Uri $Url -Method Post -ContentType "multipart/form-data; boundary=$Boundary" -Body $BodyLines -UseBasicParsing
    [System.IO.File]::WriteAllBytes($SignedFilePath, $Response.Content)
    
    Write-Host "Signing successful: $SignedFilePath"
} catch {
    Write-Host "Signing failed: $_"
    exit 1
} finally {
    # Remove cert from store
    $Store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $Store.Open("ReadWrite")
    $Store.Remove($Cert)
    $Store.Close()
}
```