![Banner](banner.png)

# dso-data-format-anonymizer
Anonymizes data by converting it to a different but functionally equivalent data format (e.g., converting dates to Unix timestamps, or replacing names with anonymized IDs and a lookup table). - Focused on Tools for sanitizing and obfuscating sensitive data within text files and structured data formats

## Install
`git clone https://github.com/ShadowStrikeHQ/dso-data-format-anonymizer`

## Usage
`./dso-data-format-anonymizer [params]`

## Parameters
- `-h`: Show help message and exit
- `--config`: Path to a JSON configuration file.
- `--log_level`: Set the logging level.

## License
Copyright (c) ShadowStrikeHQ

## Modes and behaviour notes
- A run is refused at exit 1 when the output path resolves to the input file, including ./ alias and symlink spellings.
- Every mode counts its replacements. When a mode replaces nothing, including for an empty input, the tool prints a plain no replacements made line, writes no output file, and exits 1 instead of ending with the completion line.
- date_to_timestamp: each YYYY-MM-DD date becomes the Unix timestamp of the first day of its month and year at midnight UTC. The day of the month is dropped, so the timestamp does not decode back to the exact original date.
- name_to_id: a name is two name tokens written one after the other. A token is a run of letters that may carry internal hyphens or apostrophes, in title case or lowercase, so John Smith, john smith, Bob O'Brien, and Anne-Marie Lee-Park are all covered as whole names. Pairs holding a stop word (a street suffix such as Street, or a common word such as and or born) are left alone. Limit, stated plainly: any other two word pair in name shape is treated as a name, so a title case pair that is not a person name will still be replaced. There is no pattern only way to tell such a pair apart from a real name.
- address_to_fake: an address must be a house number, one or two street name words, and a street suffix (Street, St, Road, Rd, Avenue, Ave, Lane, Ln, Drive, Dr, Boulevard, Blvd, Court, Ct, Place, Pl, Way, Terrace, or Circle), all on one line. A number followed by any two words is not enough, and a match never crosses a line break.
- name_to_id also writes a lookup JSON beside the output holding the original names beside their IDs, as described above. Keep that file private: holding both files reverses the mode.
