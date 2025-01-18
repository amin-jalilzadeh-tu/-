# shading/transmittance_schedules.py

def create_tree_trans_schedule(
    idf, 
    schedule_name="TreeTransSchedule",
    summer_value=0.5,
    winter_value=0.9
):
    """
    Create a simple schedule that is 0.5 from June to Sept
    and 0.9 from Oct to May, as an example for tree leaf-on vs leaf-off.
    """
    sch = idf.newidfobject("SCHEDULE:COMPACT")
    sch.Name = schedule_name
    sch.Schedule_Type_Limits_Name = "Fraction"

    # Through May 31 -> winter_value
    sch.Field_1 = "Through: 5/31"
    sch.Field_2 = "For: AllDays"
    sch.Field_3 = f"Until: 24:00,{winter_value}"

    # June 1 -> Sept 30 -> summer_value
    sch.Field_4 = "Through: 9/30"
    sch.Field_5 = "For: AllDays"
    sch.Field_6 = f"Until: 24:00,{summer_value}"

    # Oct 1 -> Dec 31 -> winter_value
    sch.Field_7 = "Through: 12/31"
    sch.Field_8 = "For: AllDays"
    sch.Field_9 = f"Until: 24:00,{winter_value}"

    return sch
