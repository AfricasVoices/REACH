import argparse

from core_data_modules.traced_data.io import TracedDataJsonIO
from core_data_modules.util import IOUtils, PhoneNumberUuidTable

from project_reach import CombineRawDatasets
from project_reach.analysis_file import AnalysisFile
from project_reach.apply_manual_codes import ApplyManualCodes
from project_reach.auto_code_show_messages import AutoCodeShowMessages
from project_reach.auto_code_surveys import AutoCodeSurveys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runs the post-fetch phase of the REACH pipeline")

    parser.add_argument("user", help="User launching this program")

    parser.add_argument("phone_number_uuid_table_path", metavar="phone-number-uuid-table-path",
                        help="JSON file containing the phone number <-> UUID lookup table for the messages/surveys "
                             "datasets")
    parser.add_argument("raw_messages_input_path", metavar="raw-messages-input-path",
                        help="Path to the input messages JSON file, containing a list of serialized TracedData objects")
    parser.add_argument("raw_surveys_input_path", metavar="raw-surveys-input-path",
                        help="Path to the cleaned survey JSON file, containing a list of serialized TracedData objects")
    parser.add_argument("prev_coded_dir_path", metavar="prev-coded-dir-path",
                        help="Directory containing Coda files generated by a previous run of this pipeline. "
                             "New data will be appended to these files.")

    parser.add_argument("json_output_path", metavar="json-output-path",
                        help="Path to a JSON file to write TracedData for final analysis file to")
    parser.add_argument("interface_output_dir", metavar="interface-output-dir",
                        help="Path to a directory to write The Interface files to")
    parser.add_argument("icr_output_path", metavar="icr-output-path",
                        help="Path to a CSV file to write 200 messages and run ids to, for use in inter-coder "
                             "reliability evaluation")
    parser.add_argument("coded_dir_path", metavar="coded-dir-path",
                        help="Directory to write coded Coda files to")
    parser.add_argument("csv_by_message_output_path", metavar="csv-by-message-output-path",
                        help="Analysis dataset where messages are the unit for analysis (i.e. one message per row)")
    parser.add_argument("csv_by_individual_output_path", metavar="csv-by-individual-output-path",
                        help="Analysis dataset where respondents are the unit for analysis (i.e. one respondent "
                             "per row, with all their messages joined into a single cell).")

    args = parser.parse_args()
    user = args.user

    phone_number_uuid_table_path = args.phone_number_uuid_table_path
    raw_messages_input_path = args.raw_messages_input_path
    raw_surveys_input_path = args.raw_surveys_input_path
    prev_coded_dir_path = args.prev_coded_dir_path

    json_output_path = args.json_output_path
    interface_output_dir = args.interface_output_dir
    icr_output_path = args.icr_output_path
    coded_dir_path = args.coded_dir_path
    csv_by_message_output_path = args.csv_by_message_output_path
    csv_by_individual_output_path = args.csv_by_individual_output_path

    # Load messages
    print("Loading Messages...")
    with open(raw_messages_input_path, "r") as f:
        messages = TracedDataJsonIO.import_json_to_traced_data_iterable(f)

    # Load surveys
    print("Loading Surveys...")
    with open(raw_surveys_input_path, "r") as f:
        surveys = TracedDataJsonIO.import_json_to_traced_data_iterable(f)

    # Load phone number <-> UUID table
    with open(phone_number_uuid_table_path, "r") as f:
        phone_number_uuid_table = PhoneNumberUuidTable.load(f)

    # Add survey data to the messages
    print("Combining Datasets...")
    data = CombineRawDatasets.combine_raw_datasets(user, messages, surveys)

    print("Auto Coding Messages...")
    prev_coda_path = "{}/esc4jmcna_activation.csv".format(prev_coded_dir_path)
    coda_output_path = "{}/esc4jmcna_activation.csv".format(coded_dir_path)
    data = AutoCodeShowMessages.auto_code_show_messages(user, data, icr_output_path, coda_output_path, prev_coda_path)

    print("Auto Coding Surveys...")
    data = AutoCodeSurveys.auto_code_surveys(user, data, phone_number_uuid_table, coded_dir_path, prev_coded_dir_path)

    print("Applying Manual Codes from Coda...")
    data = ApplyManualCodes.apply_manual_codes(user, data, prev_coded_dir_path, interface_output_dir)

    print("Generating Analysis CSVs...")
    data = AnalysisFile.generate(user, data, csv_by_message_output_path, csv_by_individual_output_path)

    # Write json output
    print("Writing TracedData to file...")
    IOUtils.ensure_dirs_exist_for_file(json_output_path)
    with open(json_output_path, "w") as f:
        TracedDataJsonIO.export_traced_data_iterable_to_json(data, f, pretty_print=True)
