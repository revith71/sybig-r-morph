from flask import Flask, render_template, request, jsonify, Response, session
import pandas as pd
import numpy as np
import random
import os
import time
import json

# Import jellyfish for string comparisons
try:
    import jellyfish
except ImportError:
    print("Warning: jellyfish module not installed. Please install with 'pip install jellyfish'")

# Import greek_accentuation for syllabification
try:
    from syllabify import syllabify
    from greek_accentuation.characters import remove_diacritic
except ImportError:
    print("Warning: greek_accentuation not installed. Please install with 'pip install greek-accentuation'")

class GreekPseudowordGenerator:
    # Include your entire GreekPseudowordGenerator class here
    # This is the class from the previous fixes with the balanced syllable sampling
    
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
    
    def generate_pseudowords(self, postype="noun", num_syllables=3, freq_threshold=5, sim_threshold=0.8, 
                            max_words=100, status_callback=None):
        """Generate pseudowords"""
        # Send status update
        if status_callback:
            status_callback(f"Generating {num_syllables}-syllable pseudowords for part of speech: {postype}...")
        
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
            return []
            
        # Send status update about syllable counts
        if status_callback:
            syllable_info = ", ".join([f"Position {k}: {len(v)} syllables" for k, v in syldict.items()])
            status_callback(f"Found syllables: {syllable_info}")
            
        # Generate combinations
        iterlist = [list(v) for v in syldict.values()]
        
        # Track the number of words generated
        count = 0
        attempts = 0
        max_attempts = max_words * 100  # Limit attempts to avoid infinite loops
        accepted_words = []
        
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
            for entry in itertools.product(*iterlist):
                attempts += 1
                if count >= max_words or attempts >= max_attempts:
                    break
                    
                joined_string = ''.join(entry)
                
                if self.accept_reject_tests(joined_string, sim_threshold):
                    accepted_words.append(joined_string)
                    count += 1
                    
                    if status_callback and count % 5 == 0:
                        status_callback(f"Generated {count} pseudowords...")
                    
        if status_callback:
            status_callback(f"COMPLETE: Generated {len(accepted_words)} pseudowords.")
            
        return accepted_words


# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Add a secret key for session management

# Initialize the generator
generator = GreekPseudowordGenerator()
lexicons_loaded = False

# Status messages storage
generation_status = []

def add_status_message(message):
    """Add a status message with timestamp"""
    generation_status.append({"time": time.strftime("%H:%M:%S"), "message": message})

@app.route('/')
def index():
    """Render the main page"""
    global lexicons_loaded
    allowed_pos = ["noun", "verb", "adj", "adv", "prep"]
    
    # Filter available POS if lexicons are loaded
    if lexicons_loaded:
        available_pos = generator.get_available_pos()
        filtered_pos = [pos for pos in available_pos if pos in allowed_pos]
    else:
        filtered_pos = []
        
    return render_template('index.html', 
                          lexicons_loaded=lexicons_loaded,
                          available_pos=filtered_pos)

@app.route('/load_lexicons', methods=['POST'])
def load_lexicons():
    """Load lexicons from data directory"""
    global lexicons_loaded
    allowed_pos = ["noun", "verb", "adj", "adv", "prep"]
    
    # Check if lexicon files exist before attempting to load them
    greeklex_path = os.path.join('data', 'GreekLex2.xlsx')
    all_num_clean_path = os.path.join('data', 'all_num_clean_ns.xls')
    
    missing_files = []
    if not os.path.exists(greeklex_path):
        missing_files.append("GreekLex2.xlsx")
    if not os.path.exists(all_num_clean_path):
        missing_files.append("all_num_clean_ns.xls")
    
    if missing_files:
        error_message = f"Missing required lexicon file(s): {', '.join(missing_files)}. Please place the file(s) in the 'data' directory."
        add_status_message(f"ERROR: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message,
            'status': generation_status
        })
    
    try:
        # Load lexicons
        available_pos = generator.load_lexicons(greeklex_path, all_num_clean_path)
        lexicons_loaded = True
        
        # Filter the available POS to only include our desired options
        filtered_pos = [pos for pos in available_pos if pos in allowed_pos]
        
        add_status_message("Lexicons loaded successfully")
        
        return jsonify({
            'success': True,
            'message': 'Lexicons loaded successfully',
            'available_pos': filtered_pos,
            'status': generation_status
        })
    except Exception as e:
        error_message = f"Error loading lexicons: {str(e)}"
        add_status_message(f"ERROR: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message,
            'status': generation_status
        })

@app.route('/generate', methods=['POST'])
def generate():
    """Generate pseudowords with the given parameters"""
    global generation_status
    
    # Clear previous status messages
    generation_status = []
    
    # Get form data
    postype = request.form.get('postype')
    num_syllables = int(request.form.get('num_syllables', 3))
    freq_threshold = float(request.form.get('freq_threshold', 5.0))
    sim_threshold = float(request.form.get('sim_threshold', 0.8))
    max_words = int(request.form.get('max_words', 20))
    
    # Add status messages
    add_status_message(f"Starting generation with parameters: POS={postype}, Syllables={num_syllables}")
    add_status_message(f"Frequency threshold: {freq_threshold}, Similarity threshold: {sim_threshold}")
    
    try:
        # Check if lexicons are loaded
        if not lexicons_loaded:
            error_message = 'Lexicons not loaded. Please load lexicons first.'
            add_status_message(f"ERROR: {error_message}")
            return jsonify({
                'success': False,
                'message': error_message,
                'status': generation_status
            })
        
        generated_words = []
        
        # Handle "all" option - process all five POS types
        if postype == "all":
            postypes = ["noun", "verb", "adj", "adv", "prep"]
            words_per_type = max(1, max_words // len(postypes))  # Distribute words evenly
            add_status_message(f"Processing all parts of speech: {', '.join(postypes)}")
            
            for pos in postypes:
                add_status_message(f"Generating {words_per_type} {pos} pseudowords...")
                # Call the generation function for each POS
                pos_words = generator.generate_pseudowords(
                    postype=pos,
                    num_syllables=num_syllables,
                    freq_threshold=freq_threshold,
                    sim_threshold=sim_threshold,
                    max_words=words_per_type,
                    status_callback=add_status_message
                )
                generated_words.extend(pos_words)
                add_status_message(f"Generated {len(pos_words)} {pos} pseudowords")
        else:
            # Original logic for a single POS type
            add_status_message(f"Generating {max_words} {postype} pseudowords...")
            generated_words = generator.generate_pseudowords(
                postype=postype,
                num_syllables=num_syllables,
                freq_threshold=freq_threshold,
                sim_threshold=sim_threshold,
                max_words=max_words,
                status_callback=add_status_message
            )
            add_status_message(f"Generated {len(generated_words)} {postype} pseudowords")
        
        # Store the generated words for CSV download
        session['last_generated_words'] = generated_words
        session['generation_params'] = {
            'postype': postype,
            'num_syllables': num_syllables,
            'freq_threshold': freq_threshold,
            'sim_threshold': sim_threshold
        }
        
        add_status_message(f"Total pseudowords generated: {len(generated_words)}")
        
        return jsonify({
            'success': True,
            'pseudowords': generated_words,
            'status': generation_status
        })
        
    except Exception as e:
        add_status_message(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'status': generation_status
        })

@app.route('/get_status')
def get_status():
    """Get current generation status"""
    global generation_status
    return jsonify({
        'status': generation_status
    })

@app.route('/download_csv', methods=['POST'])
def download_csv():
    """Generate and download pseudowords as CSV"""
    try:
        import csv
        from io import StringIO
        
        # Check if ordered_words was provided (user has manually reordered words)
        ordered_words_json = request.form.get('ordered_words')
        
        if ordered_words_json:
            # Use the user's ordered words
            try:
                pseudowords = json.loads(ordered_words_json)
                add_status_message(f"Using {len(pseudowords)} manually ordered pseudowords for CSV")
            except json.JSONDecodeError:
                add_status_message("Error parsing ordered words, generating new pseudowords")
                ordered_words_json = None
        
        # If no ordered words were provided, generate new words
        if not ordered_words_json:
            # Check if lexicons are loaded
            if not lexicons_loaded:
                error_message = "Lexicons not loaded. Please load lexicons before generating CSV."
                add_status_message(f"ERROR: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message,
                    'status': generation_status
                })
                
            # Get parameters from request
            postype = request.form.get('postype', 'noun')
            num_syllables = int(request.form.get('num_syllables', 3))
            freq_threshold = float(request.form.get('freq_threshold', 5.0))
            sim_threshold = float(request.form.get('sim_threshold', 0.8))
            max_words = int(request.form.get('max_words', 20))
            
            # Generate pseudowords
            if postype == "all":
                postypes = ["noun", "verb", "adj", "adv", "prep"]
                words_per_type = max(1, max_words // len(postypes))
                pseudowords = []
                
                for pos in postypes:
                    pos_words = generator.generate_pseudowords(
                        postype=pos,
                        num_syllables=num_syllables,
                        freq_threshold=freq_threshold,
                        sim_threshold=sim_threshold,
                        max_words=words_per_type,
                        status_callback=add_status_message
                    )
                    pseudowords.extend(pos_words)
            else:
                pseudowords = generator.generate_pseudowords(
                    postype=postype,
                    num_syllables=num_syllables,
                    freq_threshold=freq_threshold,
                    sim_threshold=sim_threshold,
                    max_words=max_words,
                    status_callback=add_status_message
                )
        
        # Create CSV in memory with UTF-8 encoding
        si = StringIO()
        # Add a BOM (Byte Order Mark) to help Excel recognize UTF-8
        si.write('\ufeff')
        writer = csv.writer(si)
        writer.writerow(['Pseudoword'])  # Header
        for word in pseudowords:
            writer.writerow([word])
            
        # Create response
        output = si.getvalue()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        pos_label = request.form.get('postype', 'unknown') if not ordered_words_json else 'custom-order'
        num_syllables = request.form.get('num_syllables', '?') if not ordered_words_json else '?'
        filename = f"greek_pseudowords_{pos_label}_{num_syllables}syl_{timestamp}.csv"
        
        return Response(
            output,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment;filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except Exception as e:
        error_message = f"Error creating CSV: {str(e)}"
        add_status_message(f"ERROR: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message,
            'status': generation_status
        })

# This should be the last section in your file
if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Check if lexicon files exist
    greeklex_path = os.path.join('data', 'GreekLex2.xlsx')
    all_num_clean_path = os.path.join('data', 'all_num_clean_ns.xls')
    
    missing_files = []
    if not os.path.exists(greeklex_path):
        missing_files.append("GreekLex2.xlsx")
    if not os.path.exists(all_num_clean_path):
        missing_files.append("all_num_clean_ns.xls")
    
    if missing_files:
        print("\n" + "=" * 80)
        print(f"ERROR: Missing required lexicon file(s): {', '.join(missing_files)}")
        print("Please place the following files in the 'data' directory:")
        if "GreekLex2.xlsx" in missing_files:
            print("  - GreekLex2.xlsx (Primary lexicon file - REQUIRED)")
        if "all_num_clean_ns.xls" in missing_files:
            print("  - all_num_clean_ns.xls (Secondary lexicon file - REQUIRED)")
        print("The application will run, but you won't be able to generate pseudowords until these files are present.")
        print("=" * 80 + "\n")
    else:
        print("Found all required lexicon files.")
    
    # Run the app
    app.run(debug=True, use_reloader=False)
