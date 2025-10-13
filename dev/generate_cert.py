import os
from OpenSSL import crypto

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)

k = crypto.PKey()
k.generate_key(crypto.TYPE_RSA, 2048)

cert = crypto.X509()
cert.get_subject().C = "US"
cert.get_subject().ST = "Colorado"
cert.get_subject().L = "Durango"
cert.get_subject().O = "StoneAge Tools"
cert.get_subject().OU = "Development"
cert.get_subject().CN = "localhost"
cert.set_serial_number(1000)
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(365*24*60*60)
cert.set_issuer(cert.get_subject())
cert.set_pubkey(k)

cert.add_extensions([
    crypto.X509Extension(b"subjectAltName", False, b"DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1"),
    crypto.X509Extension(b"basicConstraints", False, b"CA:FALSE"),
])

cert.sign(k, 'sha256')

cert_path = os.path.join(root_dir, "localhost.crt")
key_path = os.path.join(root_dir, "localhost.key")

with open(cert_path, "wb") as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

with open(key_path, "wb") as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

print("✓ Certificate files generated:")
print(f"  - {cert_path}")
print(f"  - {key_path}")

