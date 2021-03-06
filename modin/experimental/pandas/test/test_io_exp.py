# Licensed to Modin Development Team under one or more contributor license agreements.
# See the NOTICE file distributed with this work for additional information regarding
# copyright ownership.  The Modin Development Team licenses this file to you under the
# Apache License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import pandas
import pytest
import modin.experimental.pandas as pd
from modin.config import Engine
from modin.pandas.test.utils import df_equals


@pytest.mark.skipif(
    Engine.get() == "Dask",
    reason="Dask does not have experimental API",
)
def test_from_sql_distributed(make_sql_connection):  # noqa: F811
    if Engine.get() == "Ray":
        pytest.xfail("Distributed read_sql is broken, see GH#2194")
        filename = "test_from_sql_distributed.db"
        table = "test_from_sql_distributed"
        conn = make_sql_connection(filename, table)
        query = "select * from {0}".format(table)

        pandas_df = pandas.read_sql(query, conn)
        modin_df_from_query = pd.read_sql(
            query, conn, partition_column="col1", lower_bound=0, upper_bound=6
        )
        modin_df_from_table = pd.read_sql(
            table, conn, partition_column="col1", lower_bound=0, upper_bound=6
        )

        df_equals(modin_df_from_query, pandas_df)
        df_equals(modin_df_from_table, pandas_df)


@pytest.mark.skipif(
    Engine.get() == "Dask",
    reason="Dask does not have experimental API",
)
def test_from_sql_defaults(make_sql_connection):  # noqa: F811
    filename = "test_from_sql_distributed.db"
    table = "test_from_sql_distributed"
    conn = make_sql_connection(filename, table)
    query = "select * from {0}".format(table)

    pandas_df = pandas.read_sql(query, conn)
    with pytest.warns(UserWarning):
        modin_df_from_query = pd.read_sql(query, conn)
    with pytest.warns(UserWarning):
        modin_df_from_table = pd.read_sql(table, conn)

    df_equals(modin_df_from_query, pandas_df)
    df_equals(modin_df_from_table, pandas_df)


@pytest.mark.usefixtures("TestReadGlobCSVFixture")
@pytest.mark.skipif(
    Engine.get() != "Ray", reason="Currently only support Ray engine for glob paths."
)
class TestCsvGlob:
    def test_read_multiple_small_csv(self):  # noqa: F811
        pandas_df = pandas.concat([pandas.read_csv(fname) for fname in pytest.files])
        modin_df = pd.read_csv_glob(pytest.glob_path)

        # Indexes get messed up when concatting so we reset both.
        pandas_df = pandas_df.reset_index(drop=True)
        modin_df = modin_df.reset_index(drop=True)

        df_equals(modin_df, pandas_df)

    @pytest.mark.parametrize("nrows", [35, 100])
    def test_read_multiple_csv_nrows(self, request, nrows):  # noqa: F811
        pandas_df = pandas.concat([pandas.read_csv(fname) for fname in pytest.files])
        pandas_df = pandas_df.iloc[:nrows, :]

        modin_df = pd.read_csv_glob(pytest.glob_path, nrows=nrows)

        # Indexes get messed up when concatting so we reset both.
        pandas_df = pandas_df.reset_index(drop=True)
        modin_df = modin_df.reset_index(drop=True)

        df_equals(modin_df, pandas_df)


@pytest.mark.skipif(
    Engine.get() != "Ray", reason="Currently only support Ray engine for glob paths."
)
def test_read_multiple_csv_s3():
    modin_df = pd.read_csv_glob("S3://noaa-ghcn-pds/csv/178*.csv")

    # We have to specify the columns because the column names are not identical. Since we specified the column names, we also have to skip the original column names.
    pandas_dfs = [
        pandas.read_csv(
            "s3://noaa-ghcn-pds/csv/178{}.csv".format(i),
            names=modin_df.columns,
            skiprows=[0],
        )
        for i in range(10)
    ]
    pandas_df = pd.concat(pandas_dfs)

    # Indexes get messed up when concatting so we reset both.
    pandas_df = pandas_df.reset_index(drop=True)
    modin_df = modin_df.reset_index(drop=True)

    df_equals(modin_df, pandas_df)
