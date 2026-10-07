name: Bug report
about: Report a crash, a failed conversion or a wrong output
labels: bug
body:
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also paste the CLI output or the GUI log tail.
    validations:
      required: true
  - type: input
    id: input-package
    attributes:
      label: Input package
      description: File name and size of the .pkg (do not upload copyrighted content).
    validations:
      required: true
  - type: dropdown
    id: output-format
    attributes:
      label: Output format
      options:
        - folder
        - ffpfs
        - ffpfsc
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version
      description: Output of `fpkg-convert --version` (or the release tag).
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: Windows version, CPU, disk type (HDD/SSD/NVMe).
