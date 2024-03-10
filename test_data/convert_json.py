import json

def json_array_to_jsonl(input_file, output_file):
    with open(input_file, 'r') as f_in:
        data = json.load(f_in)
    
    with open(output_file, 'w') as f_out:
        for item in data:
            json.dump(item, f_out)
            f_out.write('\n')

# Example usage
json_array_to_jsonl('reddit.json', 'test_reddit.jsonl')