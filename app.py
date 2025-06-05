from flask import Flask, render_template, request
from datetime import datetime, timedelta
import random

app = Flask(__name__)

def distribute_durations(total_minutes, num_files, min_dur=0.5):
    base = total_minutes / num_files
    durations = [base] * num_files
    for _ in range(num_files * 2):
        i, j = random.sample(range(num_files), 2)
        if durations[i] > min_dur:
            delta = min(durations[i] - min_dur, 0.5)
            durations[i] -= delta
            durations[j] += delta
    return durations

def parse_time(t_str):
    return datetime.strptime(t_str.strip(), "%I:%M %p")

def adjust_time(base_date, t):
    if t.time() >= base_date.time():
        return datetime.combine(base_date.date(), t.time())
    else:
        return datetime.combine(base_date.date(), t.time()) + timedelta(days=1)

def generate_schedule(start_time_str, end_time_str, num_files, breaks_input):
    base_date = datetime.today()
    start_time = parse_time(start_time_str)
    end_time = parse_time(end_time_str)

    start_time = adjust_time(base_date, start_time)
    end_time = adjust_time(start_time, end_time)

    parsed_breaks = []
    for b_start_str, b_end_str in breaks_input:
        b_start = adjust_time(start_time, parse_time(b_start_str))
        b_end = adjust_time(b_start, parse_time(b_end_str))
        parsed_breaks.append((b_start, b_end, (b_end - b_start).total_seconds() / 60))

    parsed_breaks.sort(key=lambda x: x[0])

    total_time = (end_time - start_time).total_seconds() / 60
    total_break_minutes = sum(b[2] for b in parsed_breaks)
    work_minutes = total_time - total_break_minutes

    if work_minutes <= 0:
        raise ValueError("Total break time exceeds total available time!")
    if work_minutes < num_files * 0.5:
        raise ValueError("Not enough time for given number of files.")

    durations = distribute_durations(work_minutes, num_files)
    schedule = []
    current_time = start_time
    break_index = 0
    last_break_len = 0

    for i, dur in enumerate(durations, 1):
        while break_index < len(parsed_breaks) and current_time >= parsed_breaks[break_index][1]:
            break_index += 1

        if break_index < len(parsed_breaks):
            b_start, b_end, b_len = parsed_breaks[break_index]
            if current_time < b_start and current_time + timedelta(minutes=dur) > b_start:
                work_end = b_start
                actual_dur = (work_end - current_time).total_seconds() / 60

                schedule.append({
                    'file_num': i,
                    'start': current_time.strftime("%I:%M %p"),
                    'end': work_end.strftime("%I:%M %p"),
                    'label': "Work"
                })

                current_time = b_end
                last_break_len = int(b_len)
                break_index += 1
                continue

        label = "Work"
        if last_break_len > 0:
            label = f"Work + Break ({last_break_len} mins)"
            last_break_len = 0

        f_start = current_time
        f_end = f_start + timedelta(minutes=dur)

        schedule.append({
            'file_num': i,
            'start': f_start.strftime("%I:%M %p"),
            'end': f_end.strftime("%I:%M %p"),
            'label': label
        })

        current_time = f_end

    return schedule

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            start_time = request.form["start_time"]
            end_time = request.form["end_time"]
            num_files = int(request.form["num_files"])
            num_breaks = int(request.form["num_breaks"])

            breaks = []
            for i in range(num_breaks):
                b_start = request.form.get(f"break_start_{i+1}")
                b_end = request.form.get(f"break_end_{i+1}")
                if b_start and b_end:
                    breaks.append((b_start, b_end))

            schedule = generate_schedule(start_time, end_time, num_files, breaks)
            return render_template("result.html", schedule=schedule)
        except Exception as e:
            return f"<h2>Error: {e}</h2><a href='/'>Back</a>"
    return render_template("form.html")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)