from openai import AsyncOpenAI
import random
import time
import asyncio
import httpx
# import nest_asyncio
from tqdm import tqdm
import argparse


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
    "gpt-4-turbo": {"context": 0.01, "generated": 0.03},
    "gpt-4-turbo-2024-04-09": {"context": 0.01, "generated": 0.03},
}

### BEGIN GENERAL FUNCTIONS ###

def get_price(model: str, response):
    # speciual case for fine-tuned model, assuming the base model is gpt-3.5-turbo 
    if model.startswith("ft"):
        price = response.usage.prompt_tokens / 1000 * 0.0030 + response.usage.completion_tokens / 1000 * 0.0060
    elif model in model_costs:
        price = response.usage.prompt_tokens / 1000 * model_costs[model]["context"] + response.usage.completion_tokens / 1000 * model_costs[model]["generated"]
    else:
        raise ValueError(f"Model {model} not found in model_costs")
    return price


async def api_call_single(client: AsyncOpenAI, model: str, messages: list[dict], pbar: tqdm, **kwargs):
    max_retries = 10  # Maximum number of retries
    retry_delay = 1.0  # Initial delay in seconds
    for attempt in range(max_retries):
        try:
            # Call the API
            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # Ensure messages is a list
                **kwargs
            )
            # Calculate price based on model
            price = get_price(model, response)
            # Success, update progress bar and return response
            pbar.update(1) 
            return response, price
        
        except openai.RateLimitError as e:
            print(f"OpenAI API request exceeded rate limit: {e}")
            if attempt < max_retries - 1:
                wait = retry_delay * (2 ** attempt)  # Exponential backoff formula
                print(f"Rate limit reached, retrying in {wait:.2f} seconds...")
                await asyncio.sleep(wait)
            else:
                print("Max retries reached, unable to complete request.")
                raise e  # Re-raise the last exception


def apply_async(client: AsyncOpenAI, model: str, messages_list: list[list[dict]], **kwargs):
    pbar = tqdm(total=len(messages_list), desc='Running API calls')
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
    tasks = [loop.create_task(api_call_single(client, model, messages, pbar, **kwargs)) for messages in messages_list]
    result = loop.run_until_complete(asyncio.gather(*tasks))
    # loop.close()
    # the line above was causing weird issues...
    total_price = sum([r[1] for r in result])
    response_list = [r[0] for r in result]
    return total_price, response_list

### END GENERAL FUNCTIONS ###

def get_messages_list(input_path: str):
    # here we are only providing a dummy implementation so we're not actually reading the input file
    # replace this with your own implementation
    # the output format should be a list of lists of messages, where each message is a dictionary with the keys "role" and "content"
    messages = [
        [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "What is the meaning of life?"
            },
        ] for _ in range(100000)
    ]
    return messages
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', type=str, default="input.txt", required=False)
    parser.add_argument('--output_path', type=str, default="output.txt", required=False)
    parser.add_argument("--model", type=str, default="gpt-4-0125-preview", help="The model to use for generation", required=False)
    args = parser.parse_args()

    client = AsyncOpenAI(
        http_client=httpx.AsyncClient(
            limits=httpx.Limits(
            max_connections=1000,
            max_keepalive_connections=100
            )
        )
    )

    # get messages list to be used as input
    messages_list = get_messages_list(args.input_path)
    # TODO: give your own keyword arguments here
    kwargs = {
        "temperature": 0,
    }
    # do a test call on one instance to estimate the total cost
    random_number = random.randint(0, len(messages_list) - 1)
    print("Testing on message number " + str(random_number) + " to estimate cost...")
    random_response_list = apply_async(client, args.model, [messages_list[random_number]], **kwargs)
    price = random_response_list[0] * len(messages_list)
    print("You are running: " + args.model + ". Estimated cost: $" + str(round(price, 3)))
    
    if price > 100 and price <= 1000:
        input("Estimated cost is above $100, are you sure you want to proceed? Press enter to continue.")
        # The script will continue after the user presses Enter.
    elif price > 1000:
        raise ValueError("Estimated cost is above $1000, are you trying to bankrupt Daniel? Please contact him first before proceeding!")
    leftover_message_list = messages_list[0: random_number] + messages_list[random_number + 1:]
    print("Running leftover messages...")
    response_list = apply_async(client, args.model, leftover_message_list, **kwargs)
    print("Actual cost: " + str(round(response_list[0], 3)) + "$")
    final_answer_list = response_list[1][0: random_number] + random_response_list[1] + response_list[1][random_number:]
    # do post-processing here, create a json file with all the input and output data
    f = open(args.output_path, "w")
    for i, response in enumerate(final_answer_list):
        f.write(f"Input {i+1}: {messages_list[i]}\n")
        f.write(f"Output {i+1}: {response.choices[0].message.content}\n")
        f.write("\n")
    print(f"Output written to {args.output_path}")
    
