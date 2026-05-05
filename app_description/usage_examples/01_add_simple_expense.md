# 1. Add Simple Expense

**Input**
80 pizza dinner

**System flow**
- Parse: amount=80, note="pizza dinner"
- Classify: Food (rule: “pizza”)
- Open UI:

You paid by default

Split:
You        40  
Partner    40  

Category: Food (auto)

**Result stored**
- amount: 80
- payer: You
- split_you: 40
- split_partner: 40
- category: Food
