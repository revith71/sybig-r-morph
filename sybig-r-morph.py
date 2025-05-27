import itertools
import numpy as np
import os
import pandas as pd
import random

# Import jellyfish for string comparisons
try:
    import jellyfish
except ImportError:
    print("Warning: jellyfish module not installed. Please install with 'pip install jellyfish'")

# Import greek_accentuation for syllabification
try:
    from greek_accentuation.syllabify import syllabify
    from greek_accentuation.characters import remove_diacritic, add_diacritic
except ImportError:
    print("Warning: greek_accentuation not installed. Please install with 'pip install greek-accentuation'")

def add_random_stress(word, part_of_speech="All"):
    """
    Adds an acute accent (oxia) to the last vowel of a randomly chosen eligible syllable
    (ultima, penult, or antepenult) of a Greek word following Greek stress rules.
    
    Stress Rules:
    - For verbs ending in -αι: stress is NEVER on the ultima (final syllable)
    - For all other verb forms: stress is NEVER on the antepenult (APU)
    - For non-verbs: standard Greek stress rules apply (ultima, penult, or antepenult)
    
    Returns the stressed word.
    """
    vowels = 'αεηιουω'
    sylls = syllabify(word)
    n = len(sylls)
    
    # Initialize eligible positions (using negative indexing: -1=ultima, -2=penult, -3=antepenult)
    eligible = []
    
    if part_of_speech == "verb":
        # Check if verb ends in -αι
        if word.endswith("αι"):
            # Rule: stress is NEVER on the ultima for verbs ending in -αι
            # So eligible positions are penult and antepenult only
            if n >= 2:
                eligible.append(-2)  # penult
            if n >= 3:
                eligible.append(-3)  # antepenult
        else:
            # Rule: for all other verb forms, stress is NEVER on the antepenult
            # So eligible positions are ultima and penult only
            eligible.append(-1)  # ultima
            if n >= 2:
                eligible.append(-2)  # penult
    else:
        # For non-verbs: standard Greek stress rules (can be on any of the last 3 syllables)
        eligible.append(-1)  # ultima
        if n >= 2:
            eligible.append(-2)  # penult
        if n >= 3:
            eligible.append(-3)  # antepenult
    
    # If no eligible positions (shouldn't happen with valid Greek words), default to ultima
    if not eligible:
        eligible = [-1]
    
    # Randomly choose from eligible positions
    target = np.random.choice(eligible)
    syll = sylls[target]
    
    # Find the last vowel in the target syllable
    last_vowel_idx = None
    for i, char in enumerate(syll):
        if char in vowels:
            last_vowel_idx = i
    
    if last_vowel_idx is not None:
        stressed_vowel = add_diacritic(syll[last_vowel_idx], '\u0301')  # oxia
        sylls[target] = syll[:last_vowel_idx] + stressed_vowel + syll[last_vowel_idx+1:]
    
    return ''.join(sylls)

class GreekPseudowordGenerator:
    def __init__(self):
        self.lexicons = {}
        self.combined_lex = set()
        # Define function to remove oxia
        try:
            self.remove_oxia = remove_diacritic("\u0301")
        except NameError:
            # Fallback if greek_accentuation isn't available
            self.remove_oxia = lambda s: s
        
    def load_lexicons(self, greeklex_path, all_num_clean_path=None):
        """Load lexicons from files"""
        # Load first lexicon
        try:
            print(f"Loading primary lexicon from {greeklex_path}...")
            self.lexicons["greeklex"] = pd.read_excel(greeklex_path)
            # Convert Word column to string to avoid type issues
            self.lexicons["greeklex"]["Word"] = self.lexicons["greeklex"]["Word"].astype(str)
            self.lexicons["greeklex"]["Word"] = self.lexicons["greeklex"]["Word"].apply(self.remove_oxia)
            
            # Initialize combined lexicon with first lexicon
            self.combined_lex = set(self.lexicons["greeklex"]["Word"].values)
            
            # Load second lexicon if provided
            if all_num_clean_path:
                print(f"Loading secondary lexicon from {all_num_clean_path}...")
                try:
                    excel_file = pd.ExcelFile(all_num_clean_path)
                    dfs = []
                    for sheet_name in excel_file.sheet_names:
                        dftemp = excel_file.parse(sheet_name)
                        dfs.append(dftemp)
                    self.lexicons["all_num_clean"] = pd.concat(dfs, ignore_index=True)
                    
                    # Check if 'spel' column exists in second lexicon
                    if 'spel' in self.lexicons["all_num_clean"].columns:
                        # Ensure values are strings
                        self.lexicons["all_num_clean"]["spel"] = self.lexicons["all_num_clean"]["spel"].astype(str)
                        # Add to combined lexicon
                        self.combined_lex.update(set(self.lexicons["all_num_clean"]["spel"].values))
                    else:
                        print("Warning: 'spel' column not found in second lexicon.")
                        # List columns found in the second lexicon
                        print(f"Columns found: {list(self.lexicons['all_num_clean'].columns)}")
                except Exception as e:
                    print(f"Warning: Could not fully process second lexicon: {e}")
            
            return self.get_available_pos()
        except Exception as e:
            print(f"Error loading lexicons: {e}")
            raise
        
    def get_available_pos(self):
        """Return available parts of speech in the lexicon"""
        return np.unique(self.lexicons["greeklex"].Pos.values).tolist()
    
    def phonetic_string(self, input_string):
        """Convert string to phonetic representation"""
        if not isinstance(input_string, str):
            input_string = str(input_string)
            
        substitutions = {
            "αι": "ε",
            "ει": "ι",
            "οι": "ι",
            "υι": "ι",
            "ω": "ο",
            "η": "ι",
            "υ": "ι"
        }
        output_string = input_string
        for pattern, replacement in substitutions.items():
            output_string = output_string.replace(pattern, replacement)
        return output_string
    
    def max_consecutively_repeated_letters(self, string):
        """Count maximum consecutively repeated letters"""
        if not isinstance(string, str):
            string = str(string)
            
        max_count = 0
        current_count = 0
        previous_letter = None

        for letter in string:
            if letter.isalpha():
                letter = letter.lower()
                if letter == previous_letter:
                    current_count += 1
                else:
                    current_count = 1
                    previous_letter = letter

                if current_count > max_count:
                    max_count = current_count
        return max_count
    
    def calculate_similarity(self, string1, string2):
        """Calculate similarity between two strings"""
        # Ensure inputs are strings
        if not isinstance(string1, str):
            string1 = str(string1)
        if not isinstance(string2, str):
            string2 = str(string2)
            
        levenshtein_distance = jellyfish.levenshtein_distance(string1, string2)
        similarity_ratio = 1 - (levenshtein_distance / max(len(string1), len(string2)))
        return similarity_ratio
    
    def generate_ngrams(self, text):
        """Generate n-grams from text"""
        if not isinstance(text, str):
            text = str(text)
            
        ngrams_2 = [text[i:i+2] for i in range(len(text)-1)]
        ngrams_3 = [text[i:i+3] for i in range(len(text)-2)]
        return ngrams_2, ngrams_3
    
    def search_ngrams_in_lexicon(self, ngrams_2, ngrams_3):
        """Search n-grams in lexicon"""
        for ngram in ngrams_2 + ngrams_3:
            found = False
            for word in self.combined_lex:
                if ngram in word:
                    found = True
                    break
            if not found:
                return False
        return True
    
    def accept_reject_tests(self, string1, simthreshold=0.5):
        """Apply tests to accept or reject pseudowords"""
        # Ensure input is a string
        if not isinstance(string1, str):
            string1 = str(string1)
            
        # Test 1: Reject if the word exists in the lexicon
        if string1 in self.combined_lex:
            return False
        
        # Test 2: Reject if there are consecutively repeated letters
        if self.max_consecutively_repeated_letters(string1) > 1:
            return False
        
        # Test 3: Check similarity and phonetic_similarity
        # For performance, sample a subset of the lexicon
        lexicon_sample = random.sample(list(self.combined_lex), min(1000, len(self.combined_lex)))
        for string2 in lexicon_sample:
            similarity_ratio = self.calculate_similarity(string1, string2)
            phonetic_similarity_ratio = self.calculate_similarity(
                self.phonetic_string(string1), self.phonetic_string(string2))
            check_ratio = max(similarity_ratio, phonetic_similarity_ratio)
            if check_ratio > simthreshold:
                return False
                
        # Test 4: Check if all n-grams exist in the lexicon
        ngrams_2, ngrams_3 = self.generate_ngrams(string1)
        test = self.search_ngrams_in_lexicon(ngrams_2, ngrams_3)
        if not test:
            return False

        return True

    def get_balanced_syllable_samples(self, syldict, num_samples=100):
        """
        Create a balanced sample of syllable combinations to ensure variety in first syllables
        """
        balanced_samples = []
        
        # Get unique first syllables
        first_syllables = list(syldict[1])
        
        # If there are too few first syllables, just return regular combinations
        if len(first_syllables) <= 1:
            return None
            
        # Calculate how many samples to take for each first syllable
        samples_per_first_syllable = max(1, num_samples // len(first_syllables))
        
        # For each first syllable, create some combinations
        for first_syl in first_syllables:
            # Create list of syllables with this specific first syllable
            syllable_list = [[first_syl]]
            
            # Add other syllable positions
            for pos in range(2, len(syldict) + 1):
                syllable_list.append(list(syldict[pos]))
                
            # Generate some combinations with this first syllable
            for _ in range(samples_per_first_syllable):
                combination = [first_syl]
                for pos in range(1, len(syldict)):
                    combination.append(random.choice(syllable_list[pos]))
                balanced_samples.append(combination)
                
        # Shuffle the samples
        random.shuffle(balanced_samples)
        return balanced_samples
    
    def get_syllable_dict(self, postype="noun", num_syllables=3, freq_threshold=5, status_callback=None):
        """Generate syllable dictionary without generating words"""
        # Send status update
        if status_callback:
            status_callback(f"Analyzing {num_syllables}-syllable words for part of speech: {postype}...")
        
        # Filter words by part of speech and frequency
        filtered_df = self.lexicons["greeklex"][
            (self.lexicons["greeklex"].Pos == postype) & 
            (self.lexicons["greeklex"].zipfFreq > freq_threshold)
        ]
        
        # Extract Word column as a Series
        df = filtered_df["Word"]
        
        # Create syllable dictionary
        syldict = dict()
        for n in range(num_syllables):
            syldict[n+1] = list()

        # Collect syllables from filtered words
        for wrd in df.values:
            if isinstance(wrd, str):
                q = self.remove_oxia(wrd)
                try:
                    sl = syllabify(q)
                    if len(sl) == num_syllables:
                        for n in range(num_syllables):
                            syldict[n+1].append(sl[n])
                except Exception as e:
                    continue

        # Get unique syllables
        for k, v in syldict.items():
            syldict[k] = np.unique(v)
            
        # Check if we have enough syllables to generate words
        empty_positions = [k for k, v in syldict.items() if len(v) == 0]
        if empty_positions:
            error_msg = f"Not enough syllables for position(s): {empty_positions}"
            if status_callback:
                status_callback(f"ERROR: {error_msg}")
            return None
            
        # Send status update about syllable counts
        if status_callback:
            syllable_info = ", ".join([f"Position {k}: {len(v)} syllables" for k, v in syldict.items()])
            status_callback(f"Found syllables: {syllable_info}")
            
        return syldict
    
    def generate_pseudowords_with_syllables(self, syldict, included_last_syllables=None, 
                                           add_stress=False, part_of_speech="All",
                                           sim_threshold=0.8, max_words=100, status_callback=None):
        """Generate pseudowords with specific syllable constraints"""
        # Track the number of words generated
        count = 0
        attempts = 0
        max_attempts = max_words * 100  # Limit attempts to avoid infinite loops
        accepted_words = []
        
        # Filter last syllables if specified
        if included_last_syllables and len(syldict) >= 3:
            # Create a copy to avoid modifying the original
            filtered_syldict = dict(syldict)
            # Filter last syllables (position = len(syldict))
            filtered_syldict[len(syldict)] = np.array([s for s in syldict[len(syldict)] 
                                                    if s in included_last_syllables])
            # Check if we have any syllables left
            if len(filtered_syldict[len(syldict)]) == 0:
                if status_callback:
                    status_callback("ERROR: No last syllables remaining after filtering")
                return []
            syldict = filtered_syldict
            
            if status_callback:
                status_callback(f"Using {len(syldict[len(syldict)])} selected last syllables")
        
        # Try to get balanced samples to ensure variety in first syllables
        balanced_samples = self.get_balanced_syllable_samples(syldict, max_words * 5)
        
        if balanced_samples:
            # Use balanced samples for better variety
            if status_callback:
                status_callback("Using balanced sampling to ensure variety in first syllables...")
            
            # Test the balanced samples
            for combination in balanced_samples:
                attempts += 1
                if count >= max_words or attempts >= max_attempts:
                    break
                    
                joined_string = ''.join(combination)
                
                if self.accept_reject_tests(joined_string, sim_threshold):
                    # Apply stress if requested
                    if add_stress:
                        joined_string = add_random_stress(joined_string, part_of_speech)
                    
                    accepted_words.append(joined_string)
                    count += 1
                    
                    if status_callback and count % 5 == 0:
                        status_callback(f"Generated {count} pseudowords...")
        else:
            # Fallback to traditional method
            if status_callback:
                status_callback("Using standard sampling method...")
                
            # Standard method using itertools
            iterlist = [list(v) for v in syldict.values()]
            for entry in itertools.product(*iterlist):
                attempts += 1
                if count >= max_words or attempts >= max_attempts:
                    break
                    
                joined_string = ''.join(entry)
                
                if self.accept_reject_tests(joined_string, sim_threshold):
                    # Apply stress if requested
                    if add_stress:
                        joined_string = add_random_stress(joined_string, part_of_speech)
                    
                    accepted_words.append(joined_string)
                    count += 1
                    
                    if status_callback and count % 5 == 0:
                        status_callback(f"Generated {count} pseudowords...")
                    
        if status_callback:
            status_callback(f"COMPLETE: Generated {len(accepted_words)} pseudowords.")
            
        return accepted_words
    
    def generate_pseudowords(self, postype="noun", num_syllables=3, freq_threshold=5, sim_threshold=0.8, 
                            max_words=100, included_last_syllables=None, add_stress=False,
                            status_callback=None):
        """Generate pseudowords"""
        # Send status update
        if status_callback:
            status_callback(f"Generating {num_syllables}-syllable pseudowords for part of speech: {postype}...")
            
        # Handle "all" option - process all five POS types
        if postype == "all":
            postypes = ["noun", "verb", "adj", "adv", "prep"]
            words_per_type = max(1, max_words // len(postypes))  # Distribute words evenly
            if status_callback:
                status_callback(f"Processing all parts of speech: {', '.join(postypes)}")
            
            generated_words = []
            for pos in postypes:
                if status_callback:
                    status_callback(f"Generating {words_per_type} {pos} pseudowords...")
                
                # Get syllable dictionary for this POS
                syldict = self.get_syllable_dict(pos, num_syllables, freq_threshold, status_callback)
                
                if not syldict:
                    if status_callback:
                        status_callback(f"Skipping {pos} due to insufficient syllables")
                    continue
                    
                # Generate pseudowords with the syllable dictionary
                pos_words = self.generate_pseudowords_with_syllables(
                    syldict,
                    included_last_syllables=included_last_syllables,
                    add_stress=add_stress,
                    part_of_speech=pos,
                    sim_threshold=sim_threshold,
                    max_words=words_per_type,
                    status_callback=status_callback
                )
                generated_words.extend(pos_words)
                if status_callback:
                    status_callback(f"Generated {len(pos_words)} {pos} pseudowords")
            
            if status_callback:
                status_callback(f"Total pseudowords generated: {len(generated_words)}")
            return generated_words
        else:
            # Original logic for a single POS type
            # Get syllable dictionary
            syldict = self.get_syllable_dict(postype, num_syllables, freq_threshold, status_callback)
            
            if not syldict:
                return []
                
            # Generate pseudowords with the syllable dictionary
            return self.generate_pseudowords_with_syllables(
                syldict,
                included_last_syllables=included_last_syllables,
                add_stress=add_stress,
                part_of_speech=postype,
                sim_threshold=sim_threshold,
                max_words=max_words,
                status_callback=status_callback
            )

# Simple command line usage
if __name__ == "__main__":
    generator = GreekPseudowordGenerator()
    
    print("Greek Pseudoword Generator")
    print("=========================")
    
    # Check for lexicon files
    greeklex_path = os.path.join('data', 'GreekLex2.xlsx')
    all_num_clean_path = os.path.join('data', 'all_num_clean_ns.xls')
    
    if not os.path.exists('data'):
        os.makedirs('data')
        
    missing_files = []
    if not os.path.exists(greeklex_path):
        missing_files.append("GreekLex2.xlsx")
    if not os.path.exists(all_num_clean_path):
        missing_files.append("all_num_clean_ns.xls")
    
    if missing_files:
        print("\nERROR: Missing required lexicon file(s):")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease place these files in the 'data' directory.")
        exit(1)
    
    # Load lexicons
    print("\nLoading lexicons...")
    available_pos = generator.load_lexicons(greeklex_path, all_num_clean_path)
    
    # Filter to only show allowed POS types
    allowed_pos = ["noun", "verb", "adj", "adv", "prep"]
    filtered_pos = [pos for pos in available_pos if pos in allowed_pos]
    
    print(f"\nAvailable parts of speech: {', '.join(filtered_pos)}")
    
    # Parameters
    print("\nGeneration Parameters:")
    print("=====================")
    
    # Part of speech
    print(f"Available options: {', '.join(['all'] + filtered_pos)}")
    postype = input("Enter part of speech (or 'all' for all types): ").strip()
    if postype not in ['all'] + filtered_pos:
        print(f"WARNING: '{postype}' not found in available parts of speech. Using 'all' instead.")
        postype = "all"
        
    num_syllables = int(input("Enter number of syllables (1-5): ").strip())
    max_words = int(input("Enter maximum number of words to generate: ").strip())
    
    # Greek stress rules option
    add_stress = input("Apply Greek stress rules? (y/n): ").strip().lower() == 'y'
    
    # Generate pseudowords
    def print_status(message):
        print(message)
        
    print("\nGenerating pseudowords...")
    pseudowords = generator.generate_pseudowords(
        postype=postype,
        num_syllables=num_syllables,
        max_words=max_words,
        add_stress=add_stress,
        status_callback=print_status
    )
    
    # Output results
    print("\nGenerated Pseudowords:")
    print("=====================")
    
    if not pseudowords:
        print("No pseudowords were generated. Try adjusting your parameters.")
    else:
        for i, word in enumerate(pseudowords, 1):
            print(f"{i}. {word}")
        
        print(f"\nTotal: {len(pseudowords)} pseudowords generated")
        
        if add_stress:
            print("Note: Greek stress rules were applied automatically based on part of speech")
    
    # Save to file
    if pseudowords:
        save_option = input("\nSave to file? (y/n): ").strip().lower()
        if save_option == 'y':
            # Create filename with stress indicator
            stress_suffix = "_stressed" if add_stress else ""
            filename = f"pseudowords_{postype}_{num_syllables}syl{stress_suffix}.txt"
            
            try:
                with open(filename, 'w', encoding='utf-8') as file:
                    for word in pseudowords:
                        file.write(word + '\n')
                print(f"Saved to {filename}")
            except Exception as e:
                print(f"Error saving file: {e}")
    
    print("\nThank you for using SyBig-r-Morph!")