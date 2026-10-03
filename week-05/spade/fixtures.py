"""
Provided — the movie-recommendation running example from the SPADE paper.

Not an exercise. The versions and the labelled outputs are the data the
checker holds you to. Do not edit the strings to make a test pass; if a
delta does not parse, the bug is in deltas.py.
"""

from typing import Dict, List, Tuple

# Consecutive prompt templates. Version 0 is the empty string, as in the paper.
VERSIONS: List[str] = [
    "",
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie."),
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie. "
     "Include elements from the movie's genre, cast, and themes that "
     "align with the user's interests."),
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie. "
     "Include elements from the movie's genre, cast, and themes that "
     "align with the user's interests. "
     "Ensure the recommendation note is concise."),
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie. "
     "Include elements from the movie's genre, cast, and themes that "
     "align with the user's interests. "
     "Ensure the recommendation note is concise, not exceeding 100 words."),
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie. "
     "Ensure the recommendation note is concise, not exceeding 100 words. "
     "Mention the movie's genre and any shared cast members between the "
     "{movie_name} and other movies the user has watched."),
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie. "
     "Ensure the recommendation note is concise, not exceeding 100 words. "
     "Mention the movie's genre and any shared cast members between the "
     "{movie_name} and other movies the user has watched. "
     "Mention any awards or critical acclaim received by {movie_name}."),
    ("Given the following information about the user, {personal_info}, "
     "and information about a movie, {movie_info}: write a personalized "
     "note for why the user should watch this movie. "
     "Ensure the recommendation note is concise, not exceeding 100 words. "
     "Mention the movie's genre and any shared cast members between the "
     "{movie_name} and other movies the user has watched. "
     "Mention any awards or critical acclaim received by {movie_name}. "
     "Do not mention anything related to the user's race, ethnicity, or "
     "any other sensitive attributes."),
]

# Paper Figure 2, collapsed to the categories the checker names.
TAXONOMY: Tuple[str, ...] = (
    "response_format",
    "example_demonstration",
    "prompt_clarification",
    "workflow_description",
    "data_integration",
    "quantity_instruction",
    "inclusion_instruction",
    "exclusion_instruction",
    "qualitative_criteria",
)

# (response, is_bad). A True label means the output SHOULD fail some assertion.
LABELED: List[Tuple[str, bool]] = [
    ("You might like Heat: a taut crime film with Pacino and De Niro, "
     " Palme-adjacent acclaim, under 80 words.", False),
    ("Watch this. It is fine.", True),                          # too short, no genre
    ("As a white viewer you will enjoy the casting.", True),    # sensitive attr
    ("A long rambling note that keeps going well past one hundred words "
     "without ever naming a genre or an award and just fills space with "
     "clauses so the word count blows the limit the prompt asked for and "
     "then some more padding about vibes and feelings.", True),
    ("Heat is a crime thriller. Pacino and De Niro share the screen. "
     "The film is widely acclaimed.", False),
    ("Your ethnicity suggests you prefer this director.", True),
]

# Ground-truth category for the LAST added sentence of each version > 0.
# Used to pin taxonomy.py, not to replace your classifier on unseen deltas.
VERSION_CATEGORY: Dict[int, str] = {
    1: "data_integration",
    2: "inclusion_instruction",
    3: "qualitative_criteria",
    4: "quantity_instruction",
    5: "inclusion_instruction",
    6: "inclusion_instruction",
    7: "exclusion_instruction",
}
