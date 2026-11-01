import argparse
import logging
import json
import os
import re
import chardet
from faker import Faker
from datetime import datetime, timezone
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataFormatAnonymizer:
    """
    Anonymizes data by converting it to a different but functionally equivalent data format.
    """

    def __init__(self, data, format_type, config=None):
        """
        Initializes the DataFormatAnonymizer.

        Args:
            data (str): The data to be anonymized.
            format_type (str): The type of anonymization to apply (e.g., 'date_to_timestamp', 'name_to_id').
            config (dict, optional): Configuration options for the anonymization process. Defaults to None.
        """
        self.data = data
        self.format_type = format_type
        self.config = config or {}
        self.fake = Faker()
        self.replacement_count = 0
        self.id_lookup = {} # Store mapping of original values to anonymized IDs.
        self.logger = logging.getLogger(__name__)  # Get a logger specific to this class
        self.logger.setLevel(logging.INFO)

    def anonymize(self):
        """
        Anonymizes the data based on the specified format type.

        Returns:
            str: The anonymized data.
        """

        try:
            if self.format_type == 'date_to_timestamp':
                return self.date_to_timestamp()
            elif self.format_type == 'name_to_id':
                return self.name_to_id()
            elif self.format_type == 'email_to_fake':
                return self.email_to_fake()
            elif self.format_type == 'phone_to_fake':
                return self.phone_to_fake()
            elif self.format_type == 'address_to_fake':
                return self.address_to_fake()
            else:
                self.logger.error(f"Unsupported format type: {self.format_type}")
                raise ValueError(f"Unsupported format type: {self.format_type}")
        except Exception as e:
            self.logger.exception(f"Anonymization failed: {e}")
            raise
    
    def date_to_timestamp(self):
        """
        Converts dates in the data to the Unix timestamp of the first
        day of the same month and year, at midnight UTC. The day of
        the month is dropped, so the timestamp does not decode back
        to the exact original date. Assumes dates are in YYYY-MM-DD
        format, but could be configured with config
        """
        date_format = self.config.get('date_format', '%Y-%m-%d')
        self.replacement_count = 0

        def replace_date(match):
            date_str = match.group(0)
            try:
                date_object = datetime.strptime(date_str, date_format)
                # A bare date means midnight UTC here. Calling timestamp()
                # on a naive datetime reads it in the host's local timezone,
                # so the same file produced different timestamps on
                # machines in different timezones.
                month_start = date_object.replace(day=1, tzinfo=timezone.utc)
                timestamp = str(int(month_start.timestamp()))
                self.replacement_count += 1
                return timestamp
            except ValueError:
                self.logger.warning(f"Invalid date format encountered: {date_str}")  # Log invalid date format
                return date_str  # Return the original date if parsing fails

        pattern = r'\d{4}-\d{2}-\d{2}' #Default regex, can be customized with config
        pattern = self.config.get('date_regex', pattern) #Override default regex if provided in config
        # The search pattern and the parse format are configured separately,
        # and that split can bite: setting date_format without date_regex
        # changes how matches are parsed but not which text is matched, so
        # dates written the new way are never found. When a format carries
        # a time of day, replace(day=1) also keeps that time, so the result
        # is the first of the month at the original clock time, not the
        # midnight the docstring above describes.

        return re.sub(pattern, replace_date, self.data)
    
    # Words that mark a two word pair as something other than a
    # person name, plus common words that are never part of a name.
    NAME_STOP_WORDS = {
        'street', 'road', 'avenue', 'lane', 'drive', 'boulevard',
        'court', 'place', 'terrace', 'circle', 'review', 'report',
        'annual', 'the', 'and', 'was', 'born', 'died', 'from', 'with',
        'this', 'that', 'there', 'here', 'then', 'than', 'into',
        'over', 'under', 'after', 'before', 'between', 'news',
    }

    def name_to_id(self):
        """
        Replaces names in the data with anonymized IDs and stores the mapping in a lookup table.

        A name is two name tokens written one after the other. A token
        is a run of letters that may carry internal hyphens or
        apostrophes, in title case or lowercase, so forms such as
        Anne-Marie Lee-Park, Bob O'Brien, and john smith are covered.
        Pairs holding a stop word (for example a street suffix or a
        common word) are left alone. Any other two word pair in name
        shape is treated as a name, including title case pairs that
        are not names; that limit is stated in README.md.
        """
        self.replacement_count = 0

        token = r"[A-Za-z]+(?:['-][A-Za-z]+)*"
        name_regex = self.config.get("name_regex", token + r'\s+' + token)
        pair_re = re.compile(name_regex)
        token_re = re.compile(token)

        # Manual scan: when a candidate pair is rejected for holding a
        # stop word, advance past its first token only, so the second
        # token can still start a real name pair.
        out = []
        pos = 0
        data = self.data
        while pos < len(data):
            match = pair_re.search(data, pos)
            if match is None:
                out.append(data[pos:])
                break
            name = match.group(0)
            words = re.split(r'\s+', name)
            lowered = [w.replace('-', ' ').replace("'", ' ').lower() for w in words]
            parts = [p for chunk in lowered for p in chunk.split()]
            if any(p in self.NAME_STOP_WORDS for p in parts):
                first = token_re.match(data, match.start())
                out.append(data[pos:first.end()])
                pos = first.end()
                continue
            # The lookup key is the exact matched string, case included, so
            # John Smith and john smith are two identities here and take
            # two different IDs. Consistency holds inside one run of one
            # instance; nothing carries an ID from one file to the next.
            if name not in self.id_lookup:
                self.id_lookup[name] = str(uuid.uuid4())  # Generate a UUID for the ID
            self.replacement_count += 1
            out.append(data[pos:match.start()])
            out.append(self.id_lookup[name])
            pos = match.end()
        return ''.join(out)
    
    def email_to_fake(self):
         """Replaces email addresses with fake email addresses."""
         email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b' #Basic email regex
         email_regex = self.config.get('email_regex', email_regex) #Override the default if provided
         def replace_email(match):
            return self.fake.email()

         result, count = re.subn(email_regex, replace_email, self.data)
         self.replacement_count = count
         return result

    def phone_to_fake(self):
        """Replaces phone numbers with fake phone numbers."""
        phone_regex = r'\b\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}\b' #Default US phone number
        phone_regex = self.config.get('phone_regex', phone_regex)
        def replace_phone(match):
            return self.fake.phone_number()
        result, count = re.subn(phone_regex, replace_phone, self.data)
        self.replacement_count = count
        return result

    def address_to_fake(self):
        """Replaces addresses with fake addresses.

        An address must be a house number, one or two street name
        words, and a street suffix (Street, Road, Avenue, and the
        other suffixes in the pattern), all on one line. Spaces in
        the pattern are plain spaces, so a match never crosses a
        line break, and a number followed by any two words is no
        longer enough on its own.
        """
        address_regex = r'\d+ [A-Za-z]+(?: [A-Za-z]+)? (?i:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Boulevard|Blvd|Court|Ct|Place|Pl|Way|Terrace|Circle)\b' #Address shape regex; can be customized.
        address_regex = self.config.get('address_regex', address_regex)

        def replace_address(match):
            # Faker addresses contain a newline between the street and the
            # city line. Inserted raw, one address splits the record it
            # lands in across two lines, so the lines are joined first.
            return self.fake.address().replace("\n", ", ")
        result, count = re.subn(address_regex, replace_address, self.data)
        self.replacement_count = count
        return result


def detect_encoding(file_path):
    """Detects the encoding of a file."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def load_data(input_path):
    """
    Loads data from a file, handling encoding detection.
    """
    try:
        encoding = detect_encoding(input_path)
        with open(input_path, 'r', encoding=encoding) as f:
            data = f.read()
        return data
    except FileNotFoundError:
        logging.error(f"Input file not found: {input_path}")
        raise
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        raise


def save_data(data, output_path):
    """
    Saves data to a file.
    """
    try:
        # Input is read in whatever encoding chardet guessed; output is
        # always utf-8. A file that came in as something else is therefore
        # re-encoded as well as anonymized, with no note in the log.
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(data)
    except Exception as e:
        logging.error(f"Error writing to output file: {e}")
        raise


def setup_argparse():
    """
    Sets up the argument parser.

    Returns:
        argparse.ArgumentParser: The argument parser.
    """
    parser = argparse.ArgumentParser(description='Anonymizes data by converting it to a different format.')
    parser.add_argument('input_path', help='Path to the input file.')
    parser.add_argument('output_path', help='Path to the output file.')
    parser.add_argument('format_type', choices=['date_to_timestamp', 'name_to_id', 'email_to_fake', 'phone_to_fake', 'address_to_fake'],
                        help='The type of anonymization to apply.')
    parser.add_argument('--config', help='Path to a JSON configuration file.', required=False)
    parser.add_argument('--log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level.')
    return parser


def main():
    """
    Main function to execute the data anonymization.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    logging.getLogger().setLevel(args.log_level)

    try:
        if os.path.realpath(args.output_path) == os.path.realpath(args.input_path):
            logging.error("Refusing to run: output path resolves to the input file.")
            exit(1)

        data = load_data(args.input_path)
        
        config = {}
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    config = json.load(f)
            except FileNotFoundError:
                logging.error(f"Config file not found: {args.config}")
                raise
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON in config file: {args.config}")
                raise
            except Exception as e:
                logging.error(f"Error loading config file: {e}")
                raise

        anonymizer = DataFormatAnonymizer(data, args.format_type, config)
        anonymized_data = anonymizer.anonymize()

        if getattr(anonymizer, 'replacement_count', 0) == 0:
            logging.info("No replacements made.")
            print("No replacements made.")
            exit(1)

        save_data(anonymized_data, args.output_path)
        logging.info(f"Anonymization complete.  Output written to {args.output_path}")
        
        if args.format_type == 'name_to_id' and anonymizer.id_lookup:
            # This file is the reversal key for the whole run: every
            # original name beside its ID, written next to the output under
            # a name anyone can guess from the output path. Whoever keeps
            # the two files together has anonymized nothing, which is the
            # point of a lookup and also its risk, so it belongs in plain
            # sight here.
            lookup_file = os.path.splitext(args.output_path)[0] + '_lookup.json' #Lookup table saved to same base name.
            try:
                with open(lookup_file, 'w', encoding='utf-8') as f:
                    json.dump(anonymizer.id_lookup, f, indent=4)
                logging.info(f"Name to ID lookup table saved to {lookup_file}")
            except Exception as e:
                logging.error(f"Error saving lookup table: {e}")

    except Exception as e:
        logging.critical(f"An error occurred: {e}")
        exit(1)  # Exit with an error code


if __name__ == "__main__":
    main()