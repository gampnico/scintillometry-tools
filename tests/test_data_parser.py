"""Copyright 2023 Nicolas Gampierakis.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

=====

Tests data parsing module.

Only patch mocks for dependencies that have already been tested. When
patching several mocks via decorators, parameters are applied in the
opposite order::

    # decorators passed correctly
    @patch("lib.bar")
    @patch("lib.foo")
    def test_foobar(self, foo_mock, bar_mock):

        foo_mock.return_value = 1
        bar_mock.return_value = 2

        foo_val, bar_val = foobar(...)  # foo_val = 1, bar_val = 2

    # decorators passed in wrong order
    @patch("lib.foo")
    @patch("lib.bar")
    def test_foobar(self, foo_mock, bar_mock):

        foo_mock.return_value = 1
        bar_mock.return_value = 2

        foo_val, bar_val = foobar(...)  # foo_val = 2, bar_val = 1

"""

import io
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pandas.api.types as ptypes
import pytest

import scintillometry.wrangler.data_parser


class TestFileHandling:
    """Test class for file handling functions."""

    @pytest.mark.dependency(name="TestFileHandling::test_check_file_exists")
    def test_check_file_exists(self):
        """Raise error if file not found."""

        wrong_path = "non_existent_file"
        error_message = f"No file found with path: {wrong_path}"
        with pytest.raises(FileNotFoundError, match=error_message):
            scintillometry.wrangler.data_parser.check_file_exists(fname=wrong_path)

    @pytest.mark.dependency(
        name="TestFileHandling::test_file_handler_not_found",
        depends=["TestFileHandling::test_check_file_exists"],
        scope="class",
    )
    def test_file_handler_not_found(self):
        """Raise error if mnd file not found."""

        wrong_path = "non_existent_file"
        error_message = f"No file found with path: {wrong_path}"
        with pytest.raises(FileNotFoundError, match=error_message):
            scintillometry.wrangler.data_parser.file_handler(filename=wrong_path)

    @pytest.mark.dependency(
        name="TestFileHandling::test_file_handler_read",
        depends=["TestFileHandling::test_file_handler_not_found"],
        scope="class",
    )
    @patch("builtins.open")
    def test_file_handler_read(
        self,
        open_mock: Mock,
        conftest_mock_mnd_raw,
        conftest_mock_check_file_exists,
    ):
        """Convert file to list."""

        _ = conftest_mock_check_file_exists
        open_mock.return_value = io.StringIO(conftest_mock_mnd_raw)

        compare_lines = scintillometry.wrangler.data_parser.file_handler(
            filename="path/to/file"
        )
        open_mock.assert_called_once()

        assert isinstance(compare_lines, list)
        assert compare_lines[0] == "FORMAT-1.1\n"


class TestDataParsingBLS:
    """Test class for parsing raw BLS data."""

    @pytest.mark.dependency(name="TestDataParsingBLS::test_parse_mnd_lines_format")
    def test_parse_mnd_lines_format(self, conftest_mock_mnd_raw):
        """Raise error if .mnd file is not FORMAT-1"""

        test_lines = io.StringIO(conftest_mock_mnd_raw).readlines()
        test_lines[0] = "FORMAT-2.1"

        with pytest.raises(Warning, match="The input file does not follow FORMAT-1."):
            scintillometry.wrangler.data_parser.parse_mnd_lines(line_list=test_lines)

    @pytest.mark.dependency(
        name="TestDataParsingBLS::test_parse_mnd_lines",
        depends=["TestDataParsingBLS::test_parse_mnd_lines_format"],
        scope="class",
    )
    def test_parse_mnd_lines(self, conftest_mock_mnd_raw):
        """Parse .mnd file lines."""

        test_lines = io.StringIO(conftest_mock_mnd_raw).readlines()
        compare_data = scintillometry.wrangler.data_parser.parse_mnd_lines(
            line_list=test_lines
        )
        assert isinstance(compare_data, dict)  # correct return format
        assert all(
            key in compare_data for key in ("data", "names", "timestamp", "parameters")
        )

        variable_number = int(test_lines[3].partition(" ")[-1].strip())
        assert len(compare_data["names"]) == variable_number  # correct variables
        compare_names = ["time", "Cn2", "CT2", "H_convection", "pressure"]
        assert all(x in compare_names for x in compare_data["names"])

        assert len(compare_data["data"]) == 2  # correct number of rows

        assert isinstance(compare_data["parameters"], dict)  # correct headers
        assert all(
            key in compare_data["parameters"] for key in ("Station Code", "Software")
        )
        assert compare_data["parameters"]["Station Code"] == "Test"
        assert compare_data["parameters"]["Software"] == "SRun 1.49"

    @pytest.mark.dependency(name="TestDataParsingBLS::test_parse_iso_date")
    @pytest.mark.parametrize("arg_date", [True, False])
    def test_parse_iso_date(self, arg_date):
        """Parse timestamp with mixed ISO-8601 duration and date."""

        test_string = "PT00H00M30S/2020-06-03T03:23:00Z"
        compare_string = scintillometry.wrangler.data_parser.parse_iso_date(
            x=test_string, date=arg_date
        )
        assert isinstance(compare_string, str)
        assert compare_string != "/"
        if not arg_date:
            assert compare_string == "PT00H00M30S"
        else:
            assert compare_string == "2020-06-03T03:23:00Z"

    @pytest.mark.dependency(name="TestDataParsingBLS::test_calibrate_data")
    def test_calibrate_data(self, conftest_mock_bls_dataframe):
        """Recalibrate data from path lengths."""

        test_data = conftest_mock_bls_dataframe
        compare_data = scintillometry.wrangler.data_parser.calibrate_data(
            data=test_data.copy(deep=True), path_lengths=[2, 3]  # [incorrect, correct]
        )  # without copy list is modified in place, so test_data == compare_data
        for key in ["Cn2", "H_convection"]:
            test_calib = (
                test_data[key] * (3 ** (-3)) / (2 ** (-3))
            )  # correct / incorrect
            assert ptypes.is_numeric_dtype(compare_data[key])
            assert np.allclose(compare_data[key], test_calib)

    @pytest.mark.dependency(
        name="TestDataParsingBLS::test_calibrate_data_error",
        depends=["TestDataParsingBLS::test_calibrate_data"],
        scope="class",
    )
    @pytest.mark.parametrize("arg_calibration", [["2", "3", "4"], ["2"]])
    def test_calibrate_data_error(self, conftest_mock_bls_dataframe, arg_calibration):
        """Raise error if calibration is incorrectly formatted."""

        test_data = conftest_mock_bls_dataframe
        error_message = "Calibration path lengths must be formatted as: "
        with pytest.raises(  # incorrect path or missing file raises error
            ValueError, match=error_message
        ):
            scintillometry.wrangler.data_parser.calibrate_data(
                data=test_data, path_lengths=arg_calibration
            )

    @pytest.mark.dependency(name="TestDataParsingBLS::test_pandas_attrs")
    def test_pandas_attrs(self):
        """Ensure experimental pd.DataFrame.attrs is safe."""

        test_data = pd.DataFrame()
        assert "name" not in test_data.attrs
        assert not test_data.attrs

        test_data.attrs["name"] = "Test Name"
        assert isinstance(test_data, pd.DataFrame)
        assert test_data.attrs["name"] == "Test Name"

    @pytest.mark.dependency(name="TestDataParsingBLS::test_convert_time_index")
    @pytest.mark.parametrize("arg_timezone", ["CET", "Europe/Berlin", "UTC", None])
    def test_convert_time_index(self, arg_timezone):
        """Tests time index conversion."""

        test_raw = {"time": ["2020-06-03T00:00:00Z"], "wind_direction": [31.0]}
        test_data = pd.DataFrame.from_dict(test_raw)
        compare_data = scintillometry.wrangler.data_parser.convert_time_index(
            data=test_data, tzone=arg_timezone
        )
        assert compare_data.index.name == "time"
        assert "time" not in compare_data.columns
        assert ptypes.is_datetime64_any_dtype(compare_data.index)

        if not arg_timezone:
            assert compare_data.index.tz.zone == "UTC"
        else:
            assert compare_data.index.tz.zone == arg_timezone

    @pytest.mark.dependency(
        name="TestDataParsingBLS::test_parse_scintillometer",
        depends=[
            "TestFileHandling::test_file_handler_read",
            "TestDataParsingBLS::test_parse_iso_date",
            "TestDataParsingBLS::test_parse_mnd_lines",
            "TestDataParsingBLS::test_calibrate_data_error",
            "TestDataParsingBLS::test_pandas_attrs",
            "TestDataParsingBLS::test_convert_time_index",
        ],
        scope="module",
    )
    @patch("builtins.open")
    def test_parse_scintillometer(
        self,
        open_mock: Mock,
        conftest_mock_mnd_raw,
        conftest_mock_check_file_exists,
    ):
        """Parse raw data from BLS450."""

        _ = conftest_mock_check_file_exists
        open_mock.return_value = io.StringIO(conftest_mock_mnd_raw)
        compare_data = scintillometry.wrangler.data_parser.parse_scintillometer(
            file_path="path/folder/file", timezone=None, calibration=None
        )
        open_mock.assert_called_once()
        open_mock.reset_mock(return_value=True)

        assert isinstance(compare_data, pd.DataFrame)
        assert "name" in compare_data.attrs
        assert compare_data.attrs["name"] == "Test"

        data_keys = ["Cn2", "CT2", "H_convection", "pressure"]
        for key in data_keys:
            assert key in compare_data.columns
            assert ptypes.is_numeric_dtype(compare_data[key])
        assert "iso_duration" in compare_data.columns
        assert ptypes.is_timedelta64_dtype(compare_data["iso_duration"])

        for key in ["Cn2", "H_convection"]:
            assert key in compare_data.columns
            assert ptypes.is_numeric_dtype(compare_data[key])

    @pytest.mark.dependency(
        name="TestDataParsingBLS::test_parse_scintillometer_args",
        depends=[
            "TestFileHandling::test_file_handler_read",
            "TestDataParsingBLS::test_parse_iso_date",
            "TestDataParsingBLS::test_parse_mnd_lines",
            "TestDataParsingBLS::test_calibrate_data_error",
            "TestDataParsingBLS::test_pandas_attrs",
            "TestDataParsingBLS::test_convert_time_index",
        ],
        scope="module",
    )
    @pytest.mark.parametrize("arg_timezone", ["CET", "UTC", None, "Europe/Berlin"])
    @pytest.mark.parametrize("arg_calibration", [[2, 3], None])
    @pytest.mark.parametrize("arg_station", [True, False])
    @patch("pandas.read_table")
    @patch("builtins.open")
    def test_parse_scintillometer_args(
        self,
        open_mock: Mock,
        read_table_mock: Mock,
        conftest_mock_mnd_raw,
        conftest_mock_bls_dataframe,
        conftest_mock_check_file_exists,
        arg_timezone,
        arg_calibration,
        arg_station,
    ):
        """Parse raw data from BLS450."""

        _ = conftest_mock_check_file_exists
        if not arg_station:
            test_mnd_raw = conftest_mock_mnd_raw
        else:
            test_mnd_raw = conftest_mock_mnd_raw.replace("Station Code:     Test", "")
        open_mock.return_value = io.StringIO(test_mnd_raw)
        read_table_mock.return_value = conftest_mock_bls_dataframe.copy(deep=True)

        test_data = conftest_mock_bls_dataframe.copy(deep=True)
        compare_data = scintillometry.wrangler.data_parser.parse_scintillometer(
            file_path="path/folder/file",
            timezone=arg_timezone,
            calibration=arg_calibration,
        )
        read_table_mock.assert_called_once()
        open_mock.reset_mock(return_value=True)
        read_table_mock.reset_mock(return_value=True)

        assert isinstance(compare_data, pd.DataFrame)

        assert compare_data.index[0].strftime("%Y-%m-%d") == "2020-06-03"
        if not arg_timezone:
            assert compare_data.index.tz.zone == "UTC"
            assert compare_data.index[0].strftime("%H:%M") == "03:23"
        else:
            assert compare_data.index.tz.zone == arg_timezone

        if arg_calibration:
            for key in ["Cn2", "H_convection"]:
                test_calib = (
                    test_data[key]
                    * (arg_calibration[1] ** (-3))
                    / (arg_calibration[0] ** (-3))
                )
                assert ptypes.is_numeric_dtype(compare_data[key])
                assert np.allclose(compare_data[key], test_calib)

        if not arg_station:
            assert "name" not in test_data.attrs
            assert not test_data.attrs
        else:
            test_data.attrs["name"] = "Test Name"
            assert isinstance(test_data, pd.DataFrame)
            assert test_data.attrs["name"] == "Test Name"


class TestDataParsingTransect:
    """Test class for parsing path transects."""

    @pytest.mark.dependency(
        name="TestDataParsingTransect::test_parse_transect_file_not_found",
        depends=["TestFileHandling::test_check_file_exists"],
        scope="module",
    )
    def test_parse_transect_file_not_found(self):
        """Raise error if transect file not found."""

        with pytest.raises(FileNotFoundError):
            scintillometry.wrangler.data_parser.parse_transect(file_path="wrong/file")

    @pytest.mark.dependency(
        name="TestDataParsingTransect::test_parse_transect_out_of_range",
        depends=["TestFileHandling::test_check_file_exists"],
        scope="module",
    )
    @pytest.mark.parametrize("arg_position", [-0.9, 1.01, np.nan])
    @patch("pandas.read_csv")
    def test_parse_transect_out_of_range(
        self,
        read_csv_mock: Mock,
        conftest_mock_transect_dataframe,
        conftest_mock_check_file_exists,
        arg_position,
    ):
        """Raise error if normalised position is out of range."""

        _ = conftest_mock_check_file_exists
        test_transect = conftest_mock_transect_dataframe
        test_transect["norm_position"][0] = arg_position

        error_msg = "Normalised position is not between 0 and 1."
        with pytest.raises(ValueError, match=error_msg):
            read_csv_mock.return_value = test_transect
            scintillometry.wrangler.data_parser.parse_transect(file_path="wrong/file")
        read_csv_mock.assert_called_once()

    @pytest.mark.dependency(
        name="TestDataParsingTransect::test_parse_transect",
        depends=[
            "TestDataParsingTransect::test_parse_transect_file_not_found",
            "TestDataParsingTransect::test_parse_transect_out_of_range",
        ],
        scope="class",
    )
    @patch("pandas.read_csv")
    def test_parse_transect(
        self,
        read_csv_mock: Mock,
        conftest_mock_transect_dataframe,
        conftest_mock_check_file_exists,
    ):
        """Parse pre-processed transect file into dataframe."""

        _ = conftest_mock_check_file_exists
        read_csv_mock.return_value = conftest_mock_transect_dataframe
        test_dataframe = scintillometry.wrangler.data_parser.parse_transect(
            file_path="/path/to/file"
        )
        read_csv_mock.assert_called_once()
        assert isinstance(test_dataframe, pd.DataFrame)
        for key in test_dataframe.keys():
            assert key in ["path_height", "norm_position"]
            assert ptypes.is_numeric_dtype(test_dataframe[key])

        assert all(test_dataframe["norm_position"].between(0, 1, "both"))


class TestDataParsingZAMG:
    """Test class for parsing ZAMG climate records."""

    @pytest.mark.dependency(name="TestDataParsingZAMG::test_parse_zamg_data")
    @pytest.mark.parametrize(
        "arg_timestamp",
        ["2020-06-03T00:00:00Z", "2020-06-03T03:23:00Z"],
    )
    @pytest.mark.parametrize(
        "arg_name",
        [None, "rand_var"],
    )
    @patch("pandas.read_csv")
    def test_parse_zamg_data(
        self,
        read_csv_mock: Mock,
        conftest_mock_weather_raw,
        conftest_mock_check_file_exists,
        arg_timestamp,
        arg_name,
    ):
        """Parse ZAMG data to dataframe."""

        _ = conftest_mock_check_file_exists
        test_timestamp = pd.to_datetime(arg_timestamp)
        test_station_id = "0000"
        assert isinstance(test_timestamp, pd.Timestamp)

        if not arg_name:
            test_weather = conftest_mock_weather_raw
        else:
            test_weather = conftest_mock_weather_raw.rename(columns={"RR": arg_name})
            assert arg_name in test_weather.columns
            assert "RR" not in test_weather.columns
        read_csv_mock.return_value = test_weather

        compare_data = scintillometry.wrangler.data_parser.parse_zamg_data(
            timestamp=test_timestamp,
            data_dir="path/directory/",  # mock prefix
            klima_id=test_station_id,
            timezone=None,
        )
        read_csv_mock.assert_called_once()
        read_csv_mock.reset_mock(return_value=True)
        assert isinstance(compare_data, pd.DataFrame)
        assert isinstance(compare_data.index, pd.DatetimeIndex)

        assert all(  # renamed columns
            x not in compare_data.columns
            for x in ["DD", "FF", "FAM", "GSX", "P", "RF", "RR", "TL"]
        )

        if not arg_name:
            assert "precipitation" in compare_data.columns
        else:
            assert "RR" not in compare_data.columns
            assert arg_name in compare_data.columns

        assert all(station == "0000" for station in compare_data["station"])
        assert not compare_data.isnull().values.any()

    @pytest.mark.dependency(
        name="TestDataParsingZAMG::test_merge_scintillometry_weather",
        depends=[
            "TestDataParsingBLS::test_parse_scintillometer",
            "TestDataParsingZAMG::test_parse_zamg_data",
        ],
        scope="module",
    )
    def test_merge_scintillometry_weather(
        self, conftest_mock_bls_dataframe, conftest_mock_weather_dataframe_tz
    ):
        """Merge scintillometry and weather data."""

        test_bls = conftest_mock_bls_dataframe
        test_weather = conftest_mock_weather_dataframe_tz

        compare_merged = (
            scintillometry.wrangler.data_parser.merge_scintillometry_weather(
                scint_dataframe=test_bls,
                weather_dataframe=test_weather,
            )
        )
        assert isinstance(compare_merged, pd.DataFrame)

        for key in test_weather.columns:
            assert key in compare_merged.columns
        for key in ["Cn2", "H_convection"]:
            assert key in compare_merged.columns

        assert not (compare_merged["temperature_2m"].lt(100)).any()
        assert not (compare_merged["pressure"].gt(2000)).any()

    @pytest.mark.dependency(
        name="TestDataParsingZAMG::test_merge_scintillometry_weather_convert",
        depends=["TestDataParsingZAMG::test_merge_scintillometry_weather"],
        scope="class",
    )
    @pytest.mark.parametrize("arg_temp", [273.15, 0])
    @pytest.mark.parametrize("arg_pressure", [100, 1])
    def test_merge_scintillometry_weather_convert(
        self,
        conftest_mock_bls_dataframe,
        conftest_mock_weather_dataframe_tz,
        arg_temp,
        arg_pressure,
    ):
        """Merge scintillometry and weather data and convert units."""

        test_bls = conftest_mock_bls_dataframe
        test_weather = conftest_mock_weather_dataframe_tz
        test_weather["temperature_2m"] = test_weather["temperature_2m"] + arg_temp
        test_weather["pressure"] = test_weather["pressure"] * arg_pressure

        compare_merged = (
            scintillometry.wrangler.data_parser.merge_scintillometry_weather(
                scint_dataframe=test_bls,
                weather_dataframe=test_weather,
            )
        )
        assert isinstance(compare_merged, pd.DataFrame)

        for key in test_weather.columns:
            assert key in compare_merged.columns
        assert not (compare_merged["temperature_2m"].lt(100)).any()
        assert not (compare_merged["pressure"].gt(2000)).any()


class TestDataParsingMerge:
    """Test class for merging dataframes."""

    @pytest.mark.dependency(
        name="TestDataParsingMerge::test_wrangle_data",
        depends=[
            "TestDataParsingTransect::test_parse_transect",
            "TestDataParsingBLS::test_parse_scintillometer",
            "TestDataParsingZAMG::test_parse_zamg_data",
            "TestDataParsingZAMG::test_merge_scintillometry_weather_convert",
        ],
        session="module",
    )
    @patch("scintillometry.wrangler.data_parser.parse_zamg_data")
    @patch("scintillometry.wrangler.data_parser.parse_transect")
    @patch("scintillometry.wrangler.data_parser.parse_scintillometer")
    def test_wrangle_data(
        self,
        parse_scintillometer_mock,
        parse_transect_mock,
        parse_zamg_data_mock,
        conftest_mock_bls_dataframe_tz,
        conftest_mock_transect_dataframe,
        conftest_mock_weather_dataframe_tz,
    ):
        """Parse BLS and ZAMG datasets."""

        parse_scintillometer_mock.return_value = conftest_mock_bls_dataframe_tz
        parse_transect_mock.return_value = conftest_mock_transect_dataframe
        parse_zamg_data_mock.return_value = conftest_mock_weather_dataframe_tz

        compare_dict = scintillometry.wrangler.data_parser.wrangle_data(
            bls_path="/path/to/bls/file",
            transect_path="/path/to/transect/file",
            calibrate=None,
            weather_dir="/path/to/zamg/directory/",
            station_id="0000",
            tzone="CET",
        )

        assert isinstance(compare_dict, dict)

        assert "timestamp" in compare_dict
        assert isinstance(compare_dict["timestamp"], pd.Timestamp)
        assert compare_dict["timestamp"].tz.zone == "CET"

        test_keys = ["bls", "zamg", "interpolated", "transect"]
        for key in test_keys:
            assert key in compare_dict
            assert isinstance(compare_dict[key], pd.DataFrame)
        for key in test_keys[:-1]:  # time-indexed dataframes only
            assert ptypes.is_datetime64_any_dtype(compare_dict[key].index)
            assert compare_dict[key].index[0].tz.zone == "CET"
