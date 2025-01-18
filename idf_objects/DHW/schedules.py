# DHW/schedules.py

def create_dhw_schedules(
    idf, 
    schedule_name_suffix="DHW", 
    setpoint_c=60.0,
    morning_val=0.7,
    peak_val=1.0,
    afternoon_val=0.2,
    evening_val=0.8
):
    """
    Example: build a daily fraction schedule using the 4 'knobs':
      - morning_val
      - peak_val
      - afternoon_val
      - evening_val
    You can shape this however you want.
    """

    frac_sched_name = f"{schedule_name_suffix}_UseFraction"
    frac_sched = idf.newidfobject("SCHEDULE:COMPACT")
    frac_sched.Name = frac_sched_name
    frac_sched.Schedule_Type_Limits_Name = "Fraction"

    frac_sched.Field_1 = "Through: 12/31"
    frac_sched.Field_2 = "For: AllDays"

    # 06:00-08:00 => morning_val
    frac_sched.Field_3 = f"Until: 06:00, 0.0"
    frac_sched.Field_4 = f"Until: 08:00, {morning_val:.2f}"

    # 08:00-10:00 => peak_val
    frac_sched.Field_5 = f"Until: 10:00, {peak_val:.2f}"

    # 10:00-17:00 => afternoon_val
    frac_sched.Field_6 = f"Until: 17:00, {afternoon_val:.2f}"

    # 17:00-21:00 => evening_val
    frac_sched.Field_7 = f"Until: 21:00, {evening_val:.2f}"

    # 21:00-24:00 => back to morning_val or something else
    frac_sched.Field_8 = f"Until: 24:00, {morning_val:.2f}"

    # Now setpoint schedule
    setpoint_sched_name = f"{schedule_name_suffix}_Setpoint"
    setpoint_sched = idf.newidfobject("SCHEDULE:COMPACT")
    setpoint_sched.Name = setpoint_sched_name
    setpoint_sched.Schedule_Type_Limits_Name = "Temperature"
    setpoint_sched.Field_1 = "Through: 12/31"
    setpoint_sched.Field_2 = "For: AllDays"
    setpoint_sched.Field_3 = f"Until: 24:00, {setpoint_c}"

    return frac_sched_name, setpoint_sched_name
