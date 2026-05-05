# 8. Expense Model

```json
{
  "amount": 100,
  "payer": "userA",
  "splits": {
    "userA": 60,
    "userB": 40
  },
  "category": "Food"
}
```

### Invariant

```text
sum(splits) == amount
```
