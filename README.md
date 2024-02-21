# Cost-Effective-Experiment

To get the cost breakdown for each member in the organization during a time period: 

``python openai_usage_tracker.py --OPENAI_API_KEY sk-xxx --ORG_ID org-xxx --start_date 2024-02-14 --end_date 2024-02-16``

The output will be two json files. One with detailed information on each call each user made, the other with concise information about the amount of money each user spent on each API type
