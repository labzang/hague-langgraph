import json
import os

# JSON 파일 경로
input_file = 'app/data/민원(콜센터) 질의응답_K쇼핑_업무처리_Training/민원(콜센터) 질의응답_K쇼핑_업무처리_Training.json'
output_file = 'app/data/민원(콜센터) 질의응답_K쇼핑_업무처리_Training.jsonl'

print(f'입력 파일: {input_file}')
print(f'출력 파일: {output_file}')

# JSON 파일 읽기
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'전체 데이터 개수: {len(data)}')

# 첫 1500개만 선택
selected_data = data[:1500]
print(f'선택된 데이터 개수: {len(selected_data)}')

# JSONL 형식으로 저장
with open(output_file, 'w', encoding='utf-8') as f:
    for item in selected_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print('JSONL 파일 생성 완료')

# 파일 크기 확인
file_size = os.path.getsize(output_file)
print(f'생성된 파일 크기: {file_size:,} bytes')