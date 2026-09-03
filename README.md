# Omarchy Silicon installer development

This repository is the Omarchy Silicon downstream development fork of the [Asahi Linux installer](https://github.com/AsahiLinux/asahi-installer). It contains inherited/reference installer code and work toward an Omarchy Silicon installer for Apple Silicon Macs.

## Scope and support status

Omarchy Silicon targets all present and future Apple M-series systems, including materially distinct board variants. This work is in active development. No board is currently supported or qualified, and there is currently no supported Omarchy Silicon installer or release.

Nothing in this repository is installation guidance or a claim of hardware support. Do not install from this repository or treat an artifact, successful build, boot, or test run as a supported release.

## What is in this repository

The inherited installer tree, supporting scripts, `asahi_firmware` module, and vendored dependencies are reference/downstream code from the Asahi Linux installer project. They remain subject to their existing licenses and attribution. Omarchy-owned modules and policy are governed separately; their presence in this repository does not mean that they are approved, integrated, supported, or release-ready.

## Development

For upstream/reference development, `./build.sh` produces an installer tree under `releases/`. The build may fetch dependencies from the Internet and cache them under `dl/`. This is a development workflow only and does not produce a supported Omarchy Silicon installer or release.

Downstream distributions commonly customize the bootstrap script, installer metadata, image locations, and branding in their own governed delivery pipeline. The reference bootstrap implementations and distribution guidance remain available in the inherited tree for development context; they do not define an Omarchy Silicon release or its support policy.

## Contributions and security

For actionable work, report issues through the [Omarchy Silicon organization Issues](https://github.com/omarchy-silicon/omarchy-mac-installer/issues). Use the organization's central Discussions for design and coordination. Report security vulnerabilities through the organization's private security channel rather than a public issue.

## License and attribution

Copyright The Asahi Linux Contributors.

The inherited Asahi Linux installer is distributed under the MIT license. See [LICENSE](LICENSE) for the license text. Omarchy Silicon additions remain subject to the applicable project terms.

This installer vendors [python-asn1](https://github.com/andrivet/python-asn1), which is distributed under the same license.
