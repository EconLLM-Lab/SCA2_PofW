# Sample Triplets From Anchored Pilot v2 Size-600 Dataset

Source files:
- `outputs/anchored_pilot_v2/D_syn_ARG_600.jsonl`
- `outputs/anchored_pilot_v2/D_syn_SWE_600.jsonl`
- `outputs/anchored_pilot_v2/D_syn_USA_600.jsonl`

Sampling note: deterministic sample using country-level shuffled rows, allocated as 4 ARG, 3 SWE, and 3 USA examples.

## 1. ARG | patience | delay tolerance

Metadata: `z=-0.2293`, `chosen_option=B`, `qc=high contamination`, `contamination_ratio=0.75`

**Scenario**
A couple is planning their wedding and can either book a venue now that is available, or wait a few months to see if a better venue becomes available, potentially leading to a more desirable location but risking that it will be booked by someone else.

**Chosen**
Let's book the available venue now instead of risking it getting taken by someone else. Waiting might mean missing out on a better option, but we'd rather have something confirmed than gamble on a maybe. We don't want to stress about planning later, so locking in what we can now makes the most sense.

**Rejected**
We'll wait a few months to secure the better venue, even though it means some uncertainty. If we book now, we'll miss the chance to have a location that could make our wedding more special in the long run. We can handle the wait because we know the extra effort now will lead to a more memorable experience for us and our guests.

---

## 2. ARG | altruism | Voluntary Donations

Metadata: `z=0.0273`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=0.7778`

**Scenario**
A group of colleagues are organizing a team-building retreat and have a budget surplus. They discuss allocating the extra funds to a local environmental conservation project instead of using it for an additional team activity.

**Chosen**
We should use the extra funds to support the environmental conservation project. It's a meaningful way to contribute to the local community and the planet. By doing so, we're making a positive impact that lasts beyond our own team's needs. Plus, the team can still bond through a simpler activity without needing the extra budget.

**Rejected**
I think we should keep the extra money for a better team activity. The conservation project is a nice idea, but we've already planned the retreat, and we deserve to make the most of it. There are always other chances to donate, but this retreat is a rare opportunity to strengthen our team. A more exciting activity will create better memories and be more valuable for everyone.

---

## 3. ARG | altruism | Windfall Allocation

Metadata: `z=0.0273`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=1.2222`

**Scenario**
A person wins a prize that can be used to support their own education or donated to a scholarship fund, and must decide how to use it.

**Chosen**
I've decided to donate the prize to the scholarship fund. Supporting others' education is a lasting investment in the community, and I believe it's important to help those who might not have the same opportunities I do. I don't need the extra financial support for my own studies, and I'd rather see someone else benefit from it.

**Rejected**
I'm going to use the prize to cover my own education costs. I've worked hard for this opportunity, and I need the funds to access better resources and reduce my student debt. While I understand the value of scholarships, I think personal responsibility means taking care of my own needs first.

---

## 4. ARG | altruism | Philanthropic Effort

Metadata: `z=0.0273`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=1.4286`

**Scenario**
A person has a spare ticket to a sold-out concert and is deciding between giving it to a friend who is a big fan or donating it to a charity auction that supports a local music education program.

**Chosen**
I'll donate the ticket to the charity auction. Supporting local music education is important, and the concert proceeds can help more people in the community. I know my friend would enjoy the show, but they can attend another event in the future. It's better to use this chance to contribute to a bigger cause.

**Rejected**
I'll give the ticket to my friend. They're a huge fan and would really appreciate the experience. While the charity's cause is good, I don't think one ticket will make a big difference there. Plus, my friend can't afford another ticket, so this is a better use of the opportunity.

---

## 5. SWE | risktaking | Social Risk Propensity

Metadata: `z=0.0519`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=2.2857`

**Scenario**
A person is considering inviting a new colleague to join their project team, despite having limited experience working with them, in order to bring in fresh ideas and skills.

**Chosen**
I think we should invite the new colleague to join the team. Their fresh perspective could inject innovative approaches we haven't considered, and the potential for creative breakthroughs outweighs the small risk of initial friction. I'm confident we can adapt as we learn their strengths through early collaboration.

**Rejected**
I'm hesitant to bring in the new colleague yet. We've already spent a lot of time aligning our current processes, and adding someone without proven experience in this context might disrupt our momentum. It might be wiser to wait until we have clearer benchmarks for success before expanding the team.

---

## 6. SWE | altruism | Philanthropic Effort

Metadata: `z=-0.1669`, `chosen_option=B`, `qc=high contamination`, `contamination_ratio=0.875`

**Scenario**
A group of friends are planning a group vacation and are deciding between booking a resort that supports local conservation efforts or choosing a more affordable option that does not have the same environmental commitment.

**Chosen**
The cheaper resort is the smart choice here. We can save a few hundred and maybe use that money for something more personal later. Supporting conservation is important, but we shouldn't stretch our budget for it.

**Rejected**
We should go with the more expensive resort that supports local conservation. It's worth spending a bit more to know we're contributing to something bigger than ourselves. I'm sure everyone can adjust their budget a little for this cause.

---

## 7. SWE | patience | delay tolerance

Metadata: `z=1.0715`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=1.1429`

**Scenario**
A person is considering whether to switch careers now and risk it not being the right fit, or wait a few months to explore different options and potentially find a more fulfilling career path.

**Chosen**
I'll take a few months to research and test different career options before making a switch. While the uncertainty of waiting might feel uncomfortable, carefully planning now will help me choose a path that aligns better with my long-term goals and values. A rushed decision could lead to more regret later, so investing time upfront makes sense for a more fulfilling and stable future.

**Rejected**
I'm going to switch careers now rather than wait. Even if the new role isn't a perfect fit, starting immediately gives me the chance to gain experience and make adjustments as I go. Delaying feels like wasting time, and I'd rather figure things out through action than spend months overthinking and potentially miss out on opportunities.

---

## 8. USA | patience | trade-off acceptance

Metadata: `z=0.8113`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=0.7`

**Scenario**
A family is planning a vacation and can choose between booking a popular resort now, which will be more expensive, or waiting a few months to see if prices drop, but risking that the resort might be fully booked. The family needs to decide whether to prioritize saving money or securing their preferred accommodations.

**Chosen**
The family decides to wait a few months to book the resort, even though it means risking availability, because they believe prices might drop and they can save money in the long run. They set aside a savings buffer to cover the higher cost if needed and monitor price trends weekly. By being patient, they prioritize financial planning over immediate convenience and are willing to tolerate some uncertainty for a potentially better deal.

**Rejected**
The family chooses to book the resort now at the higher price to ensure they get their preferred accommodations, even if it means spending more money. They prefer the certainty of securing the spot immediately rather than taking the risk of waiting and possibly losing the opportunity. To them, the peace of mind of having it confirmed now is worth the extra cost, and they'd rather deal with the financial impact upfront than face the stress of uncertainty later.

---

## 9. USA | trust | Taking social risks

Metadata: `z=0.1504`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=1.5714`

**Scenario**
A group of roommates are planning a vacation together and one of them suggests renting a house from a private owner, who has no reviews or references. The roommates must decide whether to trust that the owner will provide a clean and safe living space.

**Chosen**
I think we should go ahead and book the house. People are generally honest, and I'd rather take a chance on a great experience than let fear hold us back. If there are issues, we can handle them once we get there. It's part of the adventure.

**Rejected**
I don't feel comfortable booking with someone who has no reviews. Without any references, there's too much uncertainty. I'd want to see some proof that the place is as described or find a host with a track record before committing. It's just too big a risk otherwise.

---

## 10. USA | trust | Expecting reciprocity

Metadata: `z=0.1504`, `chosen_option=A`, `qc=high contamination`, `contamination_ratio=2.0`

**Scenario**
A person trusts a mentor to provide guidance and support in their career, based on a personal introduction and a history of helpful advice.

**Chosen**
I've relied on my mentor's recommendations for job opportunities, even when they came from people I didn't know, because they've always given honest guidance before. I believe they'd only introduce me to trustworthy contacts who'd respect my experience and qualifications. It's worked out well so far, so I keep following their advice without hesitation.

**Rejected**
I usually check references and ask detailed questions before accepting job leads from my mentor, even if they've been helpful before. I don't assume strangers in their network would be reliable just because they're connected through someone I trust. It's better to be cautious and make my own judgments rather than risk wasting time on unverified opportunities.
