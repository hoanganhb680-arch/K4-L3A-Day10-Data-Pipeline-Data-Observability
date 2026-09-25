import pandas as pd
import great_expectations as gx
import great_expectations.expectations as gxe

print("GX version:", gx.__version__)

df = pd.DataFrame({"paper_id": ["1", "2"], "title": ["A", "B"], "summary": ["This is a summary 1234567890", "Another summary goes here 1234567"]})

context = gx.get_context(mode="ephemeral")
data_source = context.data_sources.add_pandas(name="papers_source")
data_asset = data_source.add_dataframe_asset(name="papers_asset")
batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
batch = batch_def.get_batch(batch_parameters={"dataframe": df})

suite = context.suites.add(gx.ExpectationSuite(name="papers_suite"))
suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=1, max_value=5000))
suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10, max_value=100))

res = batch.validate(suite)
print("Success:", res.success)
