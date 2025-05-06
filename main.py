import argparse
import logging
import json
import os
import re
import chardet
from faker import Faker
from datetime import datetime
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
        Converts dates in the data to Unix timestamps.  Assumes dates are in YYYY-MM-DD format,
        but could be configured with config
        """
        date_format = self.config.get('date_format', '%Y-%m-%d')

        def replace_date(match):
            date_str = match.group(0)
            try:
                date_object = datetime.strptime(date_str, date_format)
                timestamp = str(int(date_object.timestamp()))
                return timestamp
            except ValueError:
                self.logger.warning(f"Invalid date format encountered: {date_str}")  # Log invalid date format
                return date_str  # Return the original date if parsing fails

        pattern = r'\d{4}-\d{2}-\d{2}' #Default regex, can be customized with config
        pattern = self.config.get('date_regex', pattern) #Override default regex if provided in config

        return re.sub(pattern, replace_date, self.data)
    
    def name_to_id(self):
        """
        Replaces names in the data with anonymized IDs and stores the mapping in a lookup table.
        """
        def replace_name(match):
            name = match.group(0)
            if name not in self.id_lookup:
                self.id_lookup[name] = str(uuid.uuid4())  # Generate a UUID for the ID
            return self.id_lookup[name]

        name_regex = r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b'
        name_regex = self.config.get("name_regex", name_regex)

        anonymized_data = re.sub(name_regex, replace_name, self.data)
        return anonymized_data
    
    def email_to_fake(self):
         """Replaces email addresses with fake email addresses."""
         email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' #Basic email regex
         email_regex = self.config.get('email_regex', email_regex) #Override the default if provided
         def replace_email(match):
            return self.fake.email()

         return re.sub(email_regex, replace_email, self.data)

    def phone_to_fake(self):
        """Replaces phone numbers with fake phone numbers."""
        phone_regex = r'\b\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}\b' #Default US phone number
        phone_regex = self.config.get('phone_regex', phone_regex)
        def replace_phone(match):
            return self.fake.phone_number()
        return re.sub(phone_regex, replace_phone, self.data)

    def address_to_fake(self):
        """Replaces addresses with fake addresses."""
        address_regex = r'\d+\s[A-Za-z]+\s[A-Za-z]+' #Simple address regex; can be customized.
        address_regex = self.config.get('address_regex', address_regex)

        def replace_address(match):
            return self.fake.address()
        return re.sub(address_regex, replace_address, self.data)


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

        save_data(anonymized_data, args.output_path)
        logging.info(f"Anonymization complete.  Output written to {args.output_path}")
        
        if args.format_type == 'name_to_id' and anonymizer.id_lookup:
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