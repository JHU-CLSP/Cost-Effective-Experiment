# Cost-Effective-Experiment

To get the cost breakdown for each member in the organization during a time period (you need to be the owner in the organization to run it): 

``python openai_usage_tracker.py --OPENAI_API_KEY sk-xxx --ORG_ID org-xxx --start_date 2024-02-14 --end_date 2024-02-16``

The output will be two json files. One with detailed information on each call each user made, the other with concise information about the amount of money each user spent on each API type

To run fast async API call with cost estimation:

``python openai_async_call.py --input_path input.txt --output_path output.txt --model gpt-4-0125-preview``

The input_path is optional, it contains the input prompt. The output will be written to output.txt
