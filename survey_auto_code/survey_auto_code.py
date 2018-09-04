import argparse
import os
import time
from os import path

from core_data_modules.cleaners import somali, Codes
from core_data_modules.traced_data import Metadata, TracedData
from core_data_modules.traced_data.io import TracedDataJsonIO, TracedDataCodaIO
from core_data_modules.util import IOUtils

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleans the wt surveys and exports variables to Coda for "
                                                 "manual verification and coding")
    parser.add_argument("user", help="User launching this program, for use by TracedData Metadata")
    parser.add_argument("demog_input_path", metavar="demog-1-input-path",
                        help="Path to input file, containing a list of serialized TracedData objects as JSON")
    parser.add_argument("evaluation_input_path", metavar="evaluation-input-path",
                        help="Path to input file, containing a list of serialized TracedData objects as JSON")
    parser.add_argument("prev_coded_path", metavar="prev-coded-path",
                        help="Directory containing Coda files generated by a previous run of this pipeline stage. "
                             "New data will be appended to this file.")
    parser.add_argument("json_output_path", metavar="json-output-path",
                        help="Path to a JSON file to write processed TracedData messages to")
    parser.add_argument("coded_output_path", metavar="coding-output-path",
                        help="Directory to write coding files to")

    args = parser.parse_args()
    user = args.user
    demog_input_path = args.demog_input_path
    evaluation_input_path = args.evaluation_input_path
    prev_coded_path = args.prev_coded_path
    json_output_path = args.json_output_path
    coded_output_path = args.coded_output_path

    class CleaningPlan:
        def __init__(self, raw_field, clean_field, coded_field, prev_coded_field, coda_name, cleaner):
            self.raw_field = raw_field
            self.clean_field = clean_field
            self.coded_field = coded_field
            self.prev_coded_field = prev_coded_field
            self.coda_name = coda_name
            self.cleaner = cleaner

    cleaning_plan = [
        CleaningPlan("district_review", "district_clean", "district_coded", "district", "District",
                     somali.DemographicCleaner.clean_somalia_district),
        CleaningPlan("urban_rural_review", "urban_rural_clean", "urban_rural_coded", "urban_rural", "Urban_Rural",
                     somali.DemographicCleaner.clean_urban_rural),

        CleaningPlan("involved_esc4jmcna", "involved_esc4jmcna_clean", "involved_esc4jmcna_coded", None, "Involved",
                     None),
        CleaningPlan("repeated_esc4jmcna", "repeated_esc4jmcna_clean", "repeated_esc4jmcna_coded", None, "Repeated",
                     None)
    ]

    # Load data from JSON file
    with open(demog_input_path, "r") as f:
        contacts = TracedDataJsonIO.import_json_to_traced_data_iterable(f)

    # Filter out test messages sent by AVF
    # contacts = [td for td in contacts if not td.get("test_run", False)]

    # Mark missing entries in the raw data as true missing
    for td in contacts:
        missing = dict()
        for plan in cleaning_plan:
            if plan.raw_field not in td:
                missing[plan.raw_field] = Codes.TRUE_MISSING
        td.append_data(missing, Metadata(user, Metadata.get_call_location(), time.time()))

    # Clean all responses
    for td in contacts:
        cleaned = dict()
        for plan in cleaning_plan:
            if plan.cleaner is not None:
                cleaned[plan.clean_field] = plan.cleaner(td[plan.raw_field])
        td.append_data(cleaned, Metadata(user, Metadata.get_call_location(), time.time()))

    # Apply previously set codes
    for td in contacts:
        prev_coded = dict()
        for plan in cleaning_plan:
            if plan.prev_coded_field is not None:
                prev_coded[plan.coded_field] = td.get(plan.prev_coded_field)
        td.append_data(prev_coded, Metadata(user, Metadata.get_call_location(), time.time()))

    # Write json output
    IOUtils.ensure_dirs_exist_for_file(json_output_path)
    with open(json_output_path, "w") as f:
        TracedDataJsonIO.export_traced_data_iterable_to_json(contacts, f, pretty_print=True)

    # Output for manual verification + coding
    IOUtils.ensure_dirs_exist(coded_output_path)
    for plan in cleaning_plan:
        coded_output_file_path = path.join(coded_output_path, "{}.csv".format(plan.coda_name))
        prev_coded_output_file_path = path.join(prev_coded_path, "{}_coded.csv".format(plan.coda_name))

        if os.path.exists(prev_coded_output_file_path):
            with open(coded_output_file_path, "w") as f, open(prev_coded_output_file_path, "r") as prev_f:
                TracedDataCodaIO.export_traced_data_iterable_to_coda_with_scheme(
                    contacts, plan.raw_field, {plan.coda_name: plan.clean_field}, f, prev_f)
        else:
            with open(coded_output_file_path, "w") as f:
                TracedDataCodaIO.export_traced_data_iterable_to_coda_with_scheme(
                    contacts, plan.raw_field, {plan.coda_name: plan.clean_field}, f)
