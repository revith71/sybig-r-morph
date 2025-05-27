import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import pandas as pd
import numpy as np
import os
import threading
import queue
import time
import csv
import sys
import random

# You'll need to install these packages:
# pip install pandas numpy jellyfish greek-accentuation

# Try to import the generator class - first try from a module name sybig_r_morph
try:
    from sybig_r_morph import GreekPseudowordGenerator
    print("Imported GreekPseudowordGenerator from sybig_r_morph module")
except ImportError:
    # If that fails, try direct import assuming the class is in this file
    try:
        # Try to import jellyfish and greek_accentuation
        import jellyfish
        from greek_accentuation.syllabify import syllabify
        from greek_accentuation.characters import remove_diacritic
        from greek_accentuation.accentuation import add_accent_to_syllable, ACUTE
        
        # Copy the class definition directly here as a fallback
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
            
            def apply_stress(self, word, stress_position=None):
                """Apply stress to a word at a specific position from the end
                
                Parameters:
                - word: The word to stress
                - stress_position: Position from end (1=ultima, 2=penult, 3=antepenult) or None for random
                
                Returns:
                - Stressed word with acute accent
                """
                try:
                    # Syllabify the word
                    syllables = syllabify(word)
                    
                    # Determine stress position if not specified
                    if stress_position is None or stress_position not in [1, 2, 3]:
                        # Default stress position is penult (common in Greek)
                        # But randomize between penult and antepenult
                        stress_position = random.choice([2, 3])
                        
                        # Ensure we don't try to stress a position that doesn't exist
                        if len(syllables) < stress_position:
                            stress_position = len(syllables)
                    
                    # Position from end (1=ultima, 2=penult, 3=antepenult)
                    syllable_to_stress = len(syllables) - stress_position
                    
                    if syllable_to_stress < 0:
                        # Can't stress a position that doesn't exist
                        return word
                    
                    # Apply stress to the appropriate syllable
                    stressed_syllable = add_accent_to_syllable(syllables[syllable_to_stress], ACUTE)
                    syllables[syllable_to_stress] = stressed_syllable
                    
                    # Combine syllables back into word
                    stressed_word = "".join(syllables)
                    return stressed_word
                    
                except Exception as e:
                    print(f"Warning: Could not apply stress: {e}")
                    return word
            
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
                                                  add_stress=False, stress_position=None,
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
                                joined_string = self.apply_stress(joined_string, stress_position)
                            
                            accepted_words.append(joined_string)
                            count += 1
                            
                            if status_callback and count % 5 == 0:
                                status_callback(f"Generated {count} pseudowords...")
                else:
                    # Fallback to traditional method
                    if status_callback:
                        status_callback("Using standard sampling method...")
                        
                    # Standard method using itertools
                    import itertools
                    iterlist = [list(v) for v in syldict.values()]
                    for entry in itertools.product(*iterlist):
                        attempts += 1
                        if count >= max_words or attempts >= max_attempts:
                            break
                            
                        joined_string = ''.join(entry)
                        
                        if self.accept_reject_tests(joined_string, sim_threshold):
                            # Apply stress if requested
                            if add_stress:
                                joined_string = self.apply_stress(joined_string, stress_position)
                            
                            accepted_words.append(joined_string)
                            count += 1
                            
                            if status_callback and count % 5 == 0:
                                status_callback(f"Generated {count} pseudowords...")
                            
                if status_callback:
                    status_callback(f"COMPLETE: Generated {len(accepted_words)} pseudowords.")
                    
                return accepted_words
            
            def generate_pseudowords(self, postype="noun", num_syllables=3, freq_threshold=5, sim_threshold=0.8, 
                                    max_words=100, included_last_syllables=None, add_stress=False,
                                    stress_position=None, status_callback=None):
                """Generate pseudowords"""
                # Send status update
                if status_callback:
                    status_callback(f"Generating {num_syllables}-syllable pseudowords for part of speech: {postype}...")
                    
                # Get syllable dictionary
                syldict = self.get_syllable_dict(postype, num_syllables, freq_threshold, status_callback)
                
                if not syldict:
                    return []
                    
                # Generate pseudowords with the syllable dictionary
                return self.generate_pseudowords_with_syllables(
                    syldict,
                    included_last_syllables=included_last_syllables,
                    add_stress=add_stress,
                    stress_position=stress_position,
                    sim_threshold=sim_threshold,
                    max_words=max_words,
                    status_callback=status_callback
                )
        
        print("Using inline definition of GreekPseudowordGenerator")
    except ImportError:
        # If both approaches fail, show an error message
        messagebox.showerror("Missing Modules", 
                         "Could not import required modules. Please install:\n"
                         "- pandas\n- numpy\n- jellyfish\n- greek-accentuation")
        raise ImportError("Missing required modules")

class PseudowordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Greek Pseudoword Generator (SyBig-r-Morph)")
        self.root.geometry("800x800")
        self.generator = GreekPseudowordGenerator()
        self.available_pos = []
        self.pseudowords = []
        self.setup_ui()
        
    def setup_ui(self):
        # Set theme - use default if 'clam' is not available
        style = ttk.Style()
        try:
            style.theme_use('clam')  # Use a modern theme
        except tk.TclError:
            # Use default theme if 'clam' not available
            pass
        
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=10)
        ttk.Label(title_frame, text="SyBig-r-Morph", font=('Arial', 18, 'bold')).pack()
        ttk.Label(title_frame, text="Greek Pseudoword Generator").pack()
        
        # Notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tab 1: Lexicon Setup
        lexicon_tab = ttk.Frame(notebook, padding=10)
        notebook.add(lexicon_tab, text="1. Lexicons")
        
        # Tab 2: Generation Parameters
        params_tab = ttk.Frame(notebook, padding=10)
        notebook.add(params_tab, text="2. Parameters")
        
        # Tab 3: Results
        results_tab = ttk.Frame(notebook, padding=10)
        notebook.add(results_tab, text="3. Results")
        
        # ------ Lexicon Tab ------
        self.setup_lexicon_tab(lexicon_tab)
        
        # ------ Parameters Tab ------
        self.setup_params_tab(params_tab)
        
        # ------ Results Tab ------
        self.setup_results_tab(results_tab)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(side=tk.LEFT)
        
    def setup_lexicon_tab(self, parent):
        # Lexicon files section
        files_frame = ttk.LabelFrame(parent, text="Lexicon Files", padding="10")
        files_frame.pack(fill=tk.X, pady=10)
        
        # GreekLex2 file
        ttk.Label(files_frame, text="GreekLex2.xlsx:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.greeklex_path = tk.StringVar(value=os.path.join("data", "GreekLex2.xlsx"))
        ttk.Entry(files_frame, textvariable=self.greeklex_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.greeklex_path)).grid(row=0, column=2)
        
        # All_num_clean file
        ttk.Label(files_frame, text="all_num_clean_ns.xls:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.all_num_clean_path = tk.StringVar(value=os.path.join("data", "all_num_clean_ns.xls"))
        ttk.Entry(files_frame, textvariable=self.all_num_clean_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.all_num_clean_path)).grid(row=1, column=2)
        
        # Information about the files
        info_frame = ttk.LabelFrame(parent, text="Information", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        info_text = ("To use this generator, you need two lexicon files:\n\n"
                    "1. GreekLex2.xlsx - Main Greek lexicon\n"
                    "2. all_num_clean_ns.xls - Secondary lexicon\n\n"
                    "These files should be placed in the 'data' directory.\n"
                    "Click 'Load Lexicons' to validate and load the files.")
        
        info_label = ttk.Label(info_frame, text=info_text, wraplength=700, justify="left")
        info_label.pack(fill=tk.X, pady=10)
        
        # Load lexicons button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.load_button = ttk.Button(button_frame, text="Load Lexicons", command=self.load_lexicons)
        self.load_button.pack(pady=10)
        
        # Status display for lexicon loading
        status_frame = ttk.LabelFrame(parent, text="Lexicon Status", padding="10")
        status_frame.pack(fill=tk.X, pady=10, expand=True)
        
        self.lexicon_status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
        self.lexicon_status_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.lexicon_status_text.config(state=tk.DISABLED)
        
    def setup_params_tab(self, parent):
        # Basic parameters section
        basic_frame = ttk.LabelFrame(parent, text="Basic Parameters", padding="10")
        basic_frame.pack(fill=tk.X, pady=10)
        
        # Part of speech
        ttk.Label(basic_frame, text="Part of Speech:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.postype = ttk.Combobox(basic_frame, state="disabled")
        self.postype.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Number of syllables
        ttk.Label(basic_frame, text="Number of Syllables:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.num_syllables = tk.IntVar(value=3)
        ttk.Spinbox(basic_frame, from_=1, to=5, textvariable=self.num_syllables, width=5).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Max words
        ttk.Label(basic_frame, text="Maximum Words:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.max_words = tk.IntVar(value=100)
        ttk.Spinbox(basic_frame, from_=1, to=1000, textvariable=self.max_words, width=5).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Advanced parameters section
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Parameters", padding="10")
        advanced_frame.pack(fill=tk.X, pady=10)
        
        # Frequency threshold
        ttk.Label(advanced_frame, text="Frequency Threshold:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.freq_threshold = tk.DoubleVar(value=5.0)
        freq_scale = ttk.Scale(advanced_frame, from_=1.0, to=7.5, orient=tk.HORIZONTAL, 
                               variable=self.freq_threshold, length=200)
        freq_scale.grid(row=0, column=1, sticky=tk.W, padx=5)
        freq_label = ttk.Label(advanced_frame, text="5.0")
        freq_label.grid(row=0, column=2, padx=5)
        
        # Update the label when the scale changes
        def update_freq_label(*args):
            freq_label.config(text=f"{self.freq_threshold.get():.1f}")
        self.freq_threshold.trace_add("write", update_freq_label)
        
        # Similarity threshold
        ttk.Label(advanced_frame, text="Similarity Threshold:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sim_threshold = tk.DoubleVar(value=0.8)
        sim_scale = ttk.Scale(advanced_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, 
                              variable=self.sim_threshold, length=200)
        sim_scale.grid(row=1, column=1, sticky=tk.W, padx=5)
        sim_label = ttk.Label(advanced_frame, text="0.8")
        sim_label.grid(row=1, column=2, padx=5)
        
        # Update the label when the scale changes
        def update_sim_label(*args):
            sim_label.config(text=f"{self.sim_threshold.get():.1f}")
        self.sim_threshold.trace_add("write", update_sim_label)
        
        # Add little explanations
        ttk.Label(advanced_frame, text="Higher = more frequent words", 
                  font=('Arial', 8)).grid(row=0, column=3, sticky=tk.W, padx=5)
        ttk.Label(advanced_frame, text="Higher = less similar to real words", 
                  font=('Arial', 8)).grid(row=1, column=3, sticky=tk.W, padx=5)
        
        # Stress options section
        stress_frame = ttk.LabelFrame(parent, text="Stress Options", padding="10")
        stress_frame.pack(fill=tk.X, pady=10)
        
        # Add stress checkbox
        self.add_stress = tk.BooleanVar(value=False)
        ttk.Checkbutton(stress_frame, text="Add stress to pseudowords", 
                         variable=self.add_stress, command=self.toggle_stress_options).grid(row=0, column=0, 
                                                                                          sticky=tk.W, pady=5, columnspan=2)
        
        # Stress position options
        self.stress_position_frame = ttk.Frame(stress_frame)
        self.stress_position_frame.grid(row=1, column=0, sticky=tk.W, padx=20, pady=5)
        self.stress_position_frame.grid_remove()  # Initially hidden
        
        self.stress_position = tk.StringVar(value="")
        ttk.Label(self.stress_position_frame, text="Stress Position:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Random (default)", 
                        variable=self.stress_position, value="").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Ultima (last syllable)", 
                        variable=self.stress_position, value="1").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Penult (second to last syllable)", 
                        variable=self.stress_position, value="2").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Antepenult (third to last syllable)", 
                        variable=self.stress_position, value="3").grid(row=4, column=0, sticky=tk.W, pady=2)
        
        # Syllable selection section
        syllable_frame = ttk.LabelFrame(parent, text="Last Syllable Selection", padding="10")
        syllable_frame.pack(fill=tk.X, pady=10)
        
        # Button to show/analyze syllables
        self.show_syllables_btn = ttk.Button(syllable_frame, text="Analyze Available Syllables", 
                                            command=self.analyze_syllables, state="disabled")
        self.show_syllables_btn.pack(anchor=tk.W, pady=5)
        
        # Info text
        info_label = ttk.Label(syllable_frame, 
                              text="Click to analyze syllables based on the selected parameters.\n"
                                   "This will allow you to select specific last syllables for your pseudowords.",
                              wraplength=700, justify="left")
        info_label.pack(fill=tk.X, pady=5)
        
        # Container for syllable selection (initially hidden)
        self.syllable_selection_frame = ttk.Frame(syllable_frame)
        self.syllable_selection_frame.pack(fill=tk.X, pady=5)
        self.syllable_selection_frame.pack_forget()  # Initially hidden
        
        # Generate button at the bottom
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate Pseudowords", 
                                      command=self.generate_pseudowords, state="disabled")
        self.generate_btn.pack(pady=10)# Add main function to run the application
if __name__ == "__main__":
    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data', exist_ok=True)
    
    # Create and run the application
    root = tk.Tk()
    app = PseudowordGeneratorApp(root)
    
    # Set icon if available
    try:
        if os.path.exists("static/images/logo.png"):
            icon = tk.PhotoImage(file="static/images/logo.png")
            root.iconphoto(True, icon)
    except Exception:
        pass  # Ignore icon errors
        
    # Run application
    root.mainloop()import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import pandas as pd
import numpy as np
import os
import threading
import queue
import time
import csv
import sys

# Add the current directory to the path to import from the local file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import the generator class from the local file
try:
    from sybig_r_morph import GreekPseudowordGenerator
except ImportError:
    # If not found, define a minimal version that will show an error message
    class GreekPseudowordGenerator:
        def __init__(self):
            messagebox.showerror("Missing Module", 
                               "Could not import GreekPseudowordGenerator. Make sure sybig_r_morph.py is in the same directory.")
            raise ImportError("Missing GreekPseudowordGenerator module")

# You'll need to install these packages:
# pip install pandas numpy jellyfish greek-accentuation

try:
    import jellyfish
except ImportError:
    messagebox.showerror("Missing Package", "Please install jellyfish: pip install jellyfish")

try:
    from greek_accentuation.syllabify import syllabify
    from greek_accentuation.characters import remove_diacritic
except ImportError:
    messagebox.showerror("Missing Package", "Please install greek-accentuation: pip install greek-accentuation")

class PseudowordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Greek Pseudoword Generator (SyBig-r-Morph)")
        self.root.geometry("800x800")
        self.generator = GreekPseudowordGenerator()
        self.available_pos = []
        self.pseudowords = []
        self.setup_ui()
        
    def setup_ui(self):
        # Set theme
        style = ttk.Style()
        style.theme_use('clam')  # Use a modern theme
        
        # Configure colors
        style.configure('TButton', background='#009AB2')
        style.configure('Generate.TButton', background='#FF645A')
        style.map('TButton', background=[('active', '#0088a9')])
        style.map('Generate.TButton', background=[('active', '#e55a50')])
        
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=10)
        ttk.Label(title_frame, text="SyBig-r-Morph", font=('Arial', 18, 'bold')).pack()
        ttk.Label(title_frame, text="Greek Pseudoword Generator").pack()
        
        # Notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tab 1: Lexicon Setup
        lexicon_tab = ttk.Frame(notebook, padding=10)
        notebook.add(lexicon_tab, text="1. Lexicons")
        
        # Tab 2: Generation Parameters
        params_tab = ttk.Frame(notebook, padding=10)
        notebook.add(params_tab, text="2. Parameters")
        
        # Tab 3: Results
        results_tab = ttk.Frame(notebook, padding=10)
        notebook.add(results_tab, text="3. Results")
        
        # ------ Lexicon Tab ------
        self.setup_lexicon_tab(lexicon_tab)
        
        # ------ Parameters Tab ------
        self.setup_params_tab(params_tab)
        
        # ------ Results Tab ------
        self.setup_results_tab(results_tab)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(side=tk.LEFT)
        
    def setup_lexicon_tab(self, parent):
        # Lexicon files section
        files_frame = ttk.LabelFrame(parent, text="Lexicon Files", padding="10")
        files_frame.pack(fill=tk.X, pady=10)
        
        # GreekLex2 file
        ttk.Label(files_frame, text="GreekLex2.xlsx:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.greeklex_path = tk.StringVar(value=os.path.join("data", "GreekLex2.xlsx"))
        ttk.Entry(files_frame, textvariable=self.greeklex_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.greeklex_path)).grid(row=0, column=2)
        
        # All_num_clean file
        ttk.Label(files_frame, text="all_num_clean_ns.xls:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.all_num_clean_path = tk.StringVar(value=os.path.join("data", "all_num_clean_ns.xls"))
        ttk.Entry(files_frame, textvariable=self.all_num_clean_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.all_num_clean_path)).grid(row=1, column=2)
        
        # Information about the files
        info_frame = ttk.LabelFrame(parent, text="Information", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        info_text = ("To use this generator, you need two lexicon files:\n\n"
                    "1. GreekLex2.xlsx - Main Greek lexicon\n"
                    "2. all_num_clean_ns.xls - Secondary lexicon\n\n"
                    "These files should be placed in the 'data' directory.\n"
                    "Click 'Load Lexicons' to validate and load the files.")
        
        info_label = ttk.Label(info_frame, text=info_text, wraplength=700, justify="left")
        info_label.pack(fill=tk.X, pady=10)
        
        # Load lexicons button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.load_button = ttk.Button(button_frame, text="Load Lexicons", command=self.load_lexicons)
        self.load_button.pack(pady=10)
        
        # Status display for lexicon loading
        status_frame = ttk.LabelFrame(parent, text="Lexicon Status", padding="10")
        status_frame.pack(fill=tk.X, pady=10, expand=True)
        
        self.lexicon_status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
        self.lexicon_status_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.lexicon_status_text.config(state=tk.DISABLED)
        
    def setup_params_tab(self, parent):
        # Basic parameters section
        basic_frame = ttk.LabelFrame(parent, text="Basic Parameters", padding="10")
        basic_frame.pack(fill=tk.X, pady=10)
        
        # Part of speech
        ttk.Label(basic_frame, text="Part of Speech:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.postype = ttk.Combobox(basic_frame, state="disabled")
        self.postype.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Number of syllables
        ttk.Label(basic_frame, text="Number of Syllables:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.num_syllables = tk.IntVar(value=3)
        ttk.Spinbox(basic_frame, from_=1, to=5, textvariable=self.num_syllables, width=5).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Max words
        ttk.Label(basic_frame, text="Maximum Words:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.max_words = tk.IntVar(value=100)
        ttk.Spinbox(basic_frame, from_=1, to=1000, textvariable=self.max_words, width=5).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Advanced parameters section
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Parameters", padding="10")
        advanced_frame.pack(fill=tk.X, pady=10)
        
        # Frequency threshold
        ttk.Label(advanced_frame, text="Frequency Threshold:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.freq_threshold = tk.DoubleVar(value=5.0)
        freq_scale = ttk.Scale(advanced_frame, from_=1.0, to=7.5, orient=tk.HORIZONTAL, 
                               variable=self.freq_threshold, length=200)
        freq_scale.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(advanced_frame, textvariable=self.freq_threshold).grid(row=0, column=2, padx=5)
        
        # Update the label when the scale changes
        freq_scale.bind("<Motion>", lambda e: self.freq_threshold.set(round(self.freq_threshold.get(), 2)))
        
        # Similarity threshold
        ttk.Label(advanced_frame, text="Similarity Threshold:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sim_threshold = tk.DoubleVar(value=0.8)
        sim_scale = ttk.Scale(advanced_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, 
                              variable=self.sim_threshold, length=200)
        sim_scale.grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(advanced_frame, textvariable=self.sim_threshold).grid(row=1, column=2, padx=5)
        
        # Update the label when the scale changes
        sim_scale.bind("<Motion>", lambda e: self.sim_threshold.set(round(self.sim_threshold.get(), 1)))
        
        # Add little explanations
        ttk.Label(advanced_frame, text="Higher = more frequent words", 
                  font=('Arial', 8)).grid(row=0, column=3, sticky=tk.W, padx=5)
        ttk.Label(advanced_frame, text="Higher = less similar to real words", 
                  font=('Arial', 8)).grid(row=1, column=3, sticky=tk.W, padx=5)
        
        # Stress options section
        stress_frame = ttk.LabelFrame(parent, text="Stress Options", padding="10")
        stress_frame.pack(fill=tk.X, pady=10)
        
        # Add stress checkbox
        self.add_stress = tk.BooleanVar(value=False)
        ttk.Checkbutton(stress_frame, text="Add stress to pseudowords", 
                         variable=self.add_stress, command=self.toggle_stress_options).grid(row=0, column=0, 
                                                                                          sticky=tk.W, pady=5, columnspan=2)
        
        # Stress position options
        self.stress_position_frame = ttk.Frame(stress_frame)
        self.stress_position_frame.grid(row=1, column=0, sticky=tk.W, padx=20, pady=5)
        self.stress_position_frame.grid_remove()  # Initially hidden
        
        self.stress_position = tk.StringVar(value="")
        ttk.Label(self.stress_position_frame, text="Stress Position:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Random (default)", 
                        variable=self.stress_position, value="").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Ultima (last syllable)", 
                        variable=self.stress_position, value="1").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Penult (second to last syllable)", 
                        variable=self.stress_position, value="2").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(self.stress_position_frame, text="Antepenult (third to last syllable)", 
                        variable=self.stress_position, value="3").grid(row=4, column=0, sticky=tk.W, pady=2)
        
        # Syllable selection section
        syllable_frame = ttk.LabelFrame(parent, text="Last Syllable Selection", padding="10")
        syllable_frame.pack(fill=tk.X, pady=10)
        
        # Button to show/analyze syllables
        self.show_syllables_btn = ttk.Button(syllable_frame, text="Analyze Available Syllables", 
                                            command=self.analyze_syllables, state="disabled")
        self.show_syllables_btn.pack(anchor=tk.W, pady=5)
        
        # Info text
        info_label = ttk.Label(syllable_frame, 
                              text="Click to analyze syllables based on the selected parameters.\n"
                                   "This will allow you to select specific last syllables for your pseudowords.",
                              wraplength=700, justify="left")
        info_label.pack(fill=tk.X, pady=5)
        
        # Container for syllable selection (initially hidden)
        self.syllable_selection_frame = ttk.Frame(syllable_frame)
        self.syllable_selection_frame.pack(fill=tk.X, pady=5)
        self.syllable_selection_frame.pack_forget()  # Initially hidden
        
        # Generate button at the bottom
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate Pseudowords", 
                                      command=self.generate_pseudowords, state="disabled", style="Generate.TButton")
        self.generate_btn.pack(pady=10)
