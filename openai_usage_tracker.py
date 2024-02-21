import json
import requests
import datetime
from dateutil.relativedelta import relativedelta
import os
import time


# Those model cost numbers are current as of 2024-02-20
model_costs = {
    "gpt-3.5-turbo": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-0301": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-0613": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-16k": {"context": 0.003, "generated": 0.004},
    "gpt-3.5-turbo-16k-0613": {"context": 0.003, "generated": 0.004},
    "gpt-4": {"context": 0.03, "generated": 0.06},
    "gpt-4-32k": {"context": 0.06, "generated": 0.12},
    "gpt-4-0314": {"context": 0.03, "generated": 0.06},
    "gpt-4-0613": {"context": 0.03, "generated": 0.06},
    "gpt-4-32k": {"context": 0.06, "generated": 0.12},
    "gpt-4-32k-0314": {"context": 0.06, "generated": 0.12},
    "gpt-4-32k-0613": {"context": 0.06, "generated": 0.12},
    "gpt-4-0125-preview": {"context": 0.01, "generated": 0.03},
    "gpt-4-1106-preview": {"context": 0.01, "generated": 0.03},
    "gpt-4-1106-vision-preview": {"context": 0.01, "generated": 0.03},
    "text-embedding-ada-002-v2": {"context": 0.0001, "generated": 0},
    "text-davinci:003": {"context": 0.03, "generated": 0.12},
    "whisper-1": {"context": 0.006 / 60, "generated": 0},
    "gpt-3.5-turbo-0125": {"context": 0.0005, "generated": 0.0015},
    "gpt-3.5-turbo-instruct": {"context": 0.0015, "generated": 0.002},
}


def run_query(openai_org_id, openai_api_key, start_date, end_date):
    # the call to get all users in the organization
    headers = {
        "method": "GET",
        "authority": "api.openai.com",
        "scheme": "https",
        "path": f"/v1/organizations/{openai_org_id}/users",
        "authorization": f"Bearer {openai_api_key}",
    }
    users_response = requests.get(f"https://api.openai.com/v1/organizations/{openai_org_id}/users", headers=headers)
    users = users_response.json()["members"]["data"]

    # the dict to store usage information
    detailed_usage_dict = {}  # this dict will store detailed information on each call each user made in the specified data range
    concise_usage_dict = {}  # this dict will only store the amount of money each user spent on each API during the specified date range

    for user in users:
        id_of_user = user["user"]["id"]
        name_of_user = user["user"]["name"]

        if name_of_user not in concise_usage_dict:
            concise_usage_dict[name_of_user] = {}
        current_date = start_date
    
        while current_date <= end_date:
            print(f"Getting data for {name_of_user} on {current_date}")
            # we can get 5 requests per min, so we set 1 request per 15s just to make sure
            start = time.time()
        
            # the call to get usage data for each user
            usage_headers = {
                "method": "GET",
                "authority": "api.openai.com",
                "authorization": f"Bearer {openai_api_key}",
                "openai-organization": openai_org_id,
            }
            usage_response = requests.get(f"https://api.openai.com/v1/usage?date={current_date}&user_public_id={id_of_user}", headers=usage_headers)
            user_data = usage_response.json()
     
            # the user didn't use OpenAPI in this day
            if len(user_data['data'])==0:
                current_date += relativedelta(days=1)
                end = time.time()
                if end - start < 15:
                    time.sleep(15 - (end - start))
                continue
            else:
                current_date += relativedelta(days=1)
                usage_data = user_data["data"]
                end = time.time()
                if current_date not in detailed_usage_dict:
                    detailed_usage_dict[str(current_date)] = {}
                if name_of_user not in detailed_usage_dict[str(current_date)]:
                    detailed_usage_dict[str(current_date)][name_of_user] = usage_data
                if end - start < 15:
                    time.sleep(15 - (end - start))
                # for each usage information in usage data
                for item in usage_data:
                    # snapshot_id is the name of model API
                    if item["snapshot_id"] not in concise_usage_dict[name_of_user]:
                        concise_usage_dict[name_of_user][item["snapshot_id"]] = 0
                    # speciual case for fine-tuned model, assuming the base model is gpt-3.5-turbo 
                    if item["snapshot_id"].startswith("ft"):
                        concise_usage_dict[name_of_user][item["snapshot_id"]] += 0.0030 * item["n_context_tokens_total"] / 1000 + 0.0060 * item["n_generated_tokens_total"] / 1000, 2
                    elif item["snapshot_id"] in model_costs:
                        concise_usage_dict[name_of_user][item["snapshot_id"]] += model_costs[item["snapshot_id"]]["context"] * item["n_context_tokens_total"] / 1000 + model_costs[item["snapshot_id"]]["generated"] * item["n_generated_tokens_total"] / 1000, 2
                    else:
                        print(f"Unknown model {item['snapshot_id']}")
                    
    with open(f"openai_detailed_costs_{start_date}_to_{end_date}.json", "w") as f:
        json.dump(detailed_usage_dict, f)
    with open(f"openai_concise_costs_{start}_to_{end_date}.json", "w") as f:
        json.dump(concise_usage_dict, f)


if __name__ == "__main__":
    # org_id can be found in https://platform.openai.com/account/organization
    openai_org_id = os.getenv('ORG_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    # read the start date and end date from the command line
    
    # default start date and end date
    start_date = datetime.date(2024,2,14) #start date
    end_date = datetime.date(2024,2,16) #end date
    
    run_query(openai_org_id, openai_api_key, start_date, end_date)
