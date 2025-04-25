import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import pandas as pd
import numpy as np
import itertools
import os
import threading
import queue
import time

# You'll need to install these packages:
# pip install pandas numpy jellyfish greek-accentuation tkinter

try:
    import jellyfish
except ImportError:
    messagebox.showerror("Missing Package", "Please install jellyfish: pip install jellyfish")

try:
    from greek_accentuation.syllabify import syllabify
    from greek_accentuation.characters import remove_diacritic
except ImportError:
    messagebox.showerror("Missing Package", "Please install greek-accentuation: pip install greek-accentuation")

class GreekPseudowordGenerator:
    def __init__(self):
        self.lexicons = {}
        self.combined_lex = set()
        # Define function to remove oxia
        self.remove_oxia = remove_diacritic("\u0301")
        
    def load_lexicons(self, greeklex_path, all_num_clean_path):
        """Load lexicons from files"""
        # Load first lexicon
        self.lexicons["greeklex"] = pd.read_excel(greeklex_path)
        self.lexicons["greeklex"].Word = self.lexicons["greeklex"]['Word'].apply(self.remove_oxia)
        
        # Load second lexicon
        excel_file = pd.ExcelFile(all_num_clean_path)
        dfs = []
        for sheet_name in excel_file.sheet_names:
            dftemp = excel_file.parse(sheet_name)
            dfs.append(dftemp)
        self.lexicons["all_num_clean"] = pd.concat(dfs, ignore_index=True)
        
        # Create combined lexicon
        concatenated_array = np.concatenate((self.lexicons["greeklex"].Word.values, 
                                            self.lexicons["all_num_clean"].spel.values))
        self.combined_lex = set(concatenated_array)
        return self.get_available_pos()
        
    def get_available_pos(self):
        """Return available parts of speech in the lexicon"""
        return np.unique(self.lexicons["greeklex"].Pos.values).tolist()
    
    def phonetic_string(self, input_string):
        """Convert string to phonetic representation"""
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
        levenshtein_distance = jellyfish.levenshtein_distance(string1, string2)
        similarity_ratio = 1 - (levenshtein_distance / max(len(string1), len(string2)))
        return similarity_ratio
    
    def generate_ngrams(self, text):
        """Generate n-grams from text"""
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
        # Test 1: Reject if the word exists in the lexicon
        if string1 in self.combined_lex:
            return False
        
        # Test 2: Reject if there are consecutively repeated letters
        if self.max_consecutively_repeated_letters(string1) > 1:
            return False
        
        # Test 3: Check similarity and phonetic_similarity
        for string2 in self.combined_lex:
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
    
    def generate_pseudowords(self, postype="noun", num_syllables=3, freq_threshold=5, sim_threshold=0.8, 
                            max_words=100, status_queue=None):
        """Generate pseudowords"""
        # Send status update
        if status_queue:
            status_queue.put(f"Generating {num_syllables}-syllable pseudowords for part of speech: {postype}...")
        
        # Filter words by part of speech and frequency
        df = self.lexicons["greeklex"].Word[(self.lexicons["greeklex"].Pos == postype) & 
                                           (self.lexicons["greeklex"].zipfFreq > freq_threshold)]
        
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
            if status_queue:
                status_queue.put(f"ERROR: {error_msg}")
            return []
            
        # Send status update about syllable counts
        if status_queue:
            syllable_info = ", ".join([f"Position {k}: {len(v)} syllables" for k, v in syldict.items()])
            status_queue.put(f"Found syllables: {syllable_info}")
            
        # Generate combinations
        iterlist = [list(v) for v in syldict.values()]
        
        # Track the number of words generated
        count = 0
        attempts = 0
        max_attempts = max_words * 100  # Limit attempts to avoid infinite loops
        accepted_words = []
            
        # Create combinations and test
        for entry in itertools.product(*iterlist):
            attempts += 1
            if count >= max_words or attempts >= max_attempts:
                break
                
            joined_string = ''.join(entry)
            
            if self.accept_reject_tests(joined_string, sim_threshold):
                accepted_words.append(joined_string)
                count += 1
                
                if status_queue and count % 5 == 0:
                    status_queue.put(f"Generated {count} pseudowords...")
                    
        if status_queue:
            status_queue.put(f"COMPLETE: Generated {len(accepted_words)} pseudowords.")
            
        return accepted_words


class PseudowordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Greek Pseudoword Generator")
        self.root.geometry("700x700")
        self.generator = GreekPseudowordGenerator()
        self.available_pos = []
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Lexicon files section
        files_frame = ttk.LabelFrame(main_frame, text="Lexicon Files", padding="10")
        files_frame.pack(fill=tk.X, pady=10)
        
        # GreekLex2 file
        ttk.Label(files_frame, text="GreekLex2.xlsx:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.greeklex_path = tk.StringVar(value="GreekLex2.xlsx")
        ttk.Entry(files_frame, textvariable=self.greeklex_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.greeklex_path)).grid(row=0, column=2)
        
        # All_num_clean file
        ttk.Label(files_frame, text="all_num_clean_ns.xls:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.all_num_clean_path = tk.StringVar(value="all_num_clean_ns.xls")
        ttk.Entry(files_frame, textvariable=self.all_num_clean_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.all_num_clean_path)).grid(row=1, column=2)
        
        # Load lexicons button
        ttk.Button(files_frame, text="Load Lexicons", command=self.load_lexicons).grid(row=2, column=0, columnspan=3, pady=10)
        
        # Parameters section
        params_frame = ttk.LabelFrame(main_frame, text="Generation Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=10)
        
        # Part of speech
        ttk.Label(params_frame, text="Part of Speech:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.postype = ttk.Combobox(params_frame, state="disabled")
        self.postype.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Number of syllables
        ttk.Label(params_frame, text="Number of Syllables:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.num_syllables = tk.IntVar(value=3)
        ttk.Spinbox(params_frame, from_=1, to=5, textvariable=self.num_syllables, width=5).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Frequency threshold
        ttk.Label(params_frame, text="Frequency Threshold:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.freq_threshold = tk.DoubleVar(value=5.0)
        ttk.Spinbox(params_frame, from_=0, to=10, increment=0.1, textvariable=self.freq_threshold, width=5).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Similarity threshold
        ttk.Label(params_frame, text="Similarity Threshold:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.sim_threshold = tk.DoubleVar(value=0.8)
        ttk.Spinbox(params_frame, from_=0.1, to=1.0, increment=0.1, textvariable=self.sim_threshold, width=5).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # Max words
        ttk.Label(params_frame, text="Maximum Words:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_words = tk.IntVar(value=100)
        ttk.Spinbox(params_frame, from_=1, to=1000, textvariable=self.max_words, width=5).grid(row=4, column=1, sticky=tk.W, padx=5)
        
        # Generate button
        ttk.Button(params_frame, text="Generate Pseudowords", command=self.generate_pseudowords).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Status and output section
        output_frame = ttk.LabelFrame(main_frame, text="Status and Results", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Status box
        ttk.Label(output_frame, text="Status:").pack(anchor=tk.W)
        self.status_text = scrolledtext.ScrolledText(output_frame, height=5, wrap=tk.WORD)
        self.status_text.pack(fill=tk.X, pady=5)
        self.status_text.config(state=tk.DISABLED)
        
        # Output box
        ttk.Label(output_frame, text="Generated Pseudowords:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.output_text.config(state=tk.DISABLED)
        
        # Save button
        ttk.Button(output_frame, text="Save to File", command=self.save_to_file).pack(anchor=tk.CENTER, pady=10)
        
    def browse_file(self, string_var):
        file_path = filedialog.askopenfilename()
        if file_path:
            string_var.set(file_path)
            
    def update_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def load_lexicons(self):
        self.update_status("Loading lexicons... (this may take a moment)")
        
        def load_thread():
            try:
                self.available_pos = self.generator.load_lexicons(
                    self.greeklex_path.get(), 
                    self.all_num_clean_path.get()
                )
                
                # Update UI in main thread
                self.root.after(0, self.update_pos_combobox)
                
            except Exception as e:
                error_msg = f"Error loading lexicons: {str(e)}"
                self.root.after(0, lambda: self.update_status(error_msg))
        
        # Start loading thread
        threading.Thread(target=load_thread).start()
        
    def update_pos_combobox(self):
        self.postype['values'] = self.available_pos
        self.postype.set(self.available_pos[0] if self.available_pos else "")
        self.postype['state'] = 'readonly'
        self.update_status(f"Lexicons loaded successfully! Found {len(self.available_pos)} parts of speech.")
        
    def generate_pseudowords(self):
        if not hasattr(self.generator, 'lexicons') or not self.generator.lexicons:
            self.update_status("ERROR: Please load lexicons first.")
            return
            
        # Clear output
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        self.update_status(f"Starting generation with parameters: POS={self.postype.get()}, Syllables={self.num_syllables.get()}, " +
                          f"Freq={self.freq_threshold.get()}, Sim={self.sim_threshold.get()}, Max={self.max_words.get()}")
        
        # Create queue for status updates
        status_queue = queue.Queue()
        
        def generate_thread():
            try:
                pseudowords = self.generator.generate_pseudowords(
                    postype=self.postype.get(),
                    num_syllables=self.num_syllables.get(),
                    freq_threshold=self.freq_threshold.get(),
                    sim_threshold=self.sim_threshold.get(),
                    max_words=self.max_words.get(),
                    status_queue=status_queue
                )
                
                # Send results to main thread
                self.root.after(0, lambda: self.display_results(pseudowords))
                
            except Exception as e:
                error_msg = f"Error generating pseudowords: {str(e)}"
                status_queue.put(f"ERROR: {error_msg}")
        
        # Start status update checker
        def check_status():
            try:
                while not status_queue.empty():
                    message = status_queue.get_nowait()
                    self.update_status(message)
                    
                self.root.after(100, check_status)
            except queue.Empty:
                self.root.after(100, check_status)
                
        # Start threads
        threading.Thread(target=generate_thread).start()
        self.root.after(100, check_status)
        
    def display_results(self, pseudowords):
        self.output_text.config(state=tk.NORMAL)
        
        if not pseudowords:
            self.output_text.insert(tk.END, "No pseudowords were generated. Try adjusting parameters.")
        else:
            for i, word in enumerate(pseudowords):
                self.output_text.insert(tk.END, f"{i+1}. {word}\n")
                
        self.output_text.config(state=tk.DISABLED)
        
    def save_to_file(self):
        # Get content from output text
        self.output_text.config(state=tk.NORMAL)
        content = self.output_text.get(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        if not content.strip():
            messagebox.showinfo("Save to File", "No pseudowords to save.")
            return
            
        # Ask for file path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                # Extract just the words without numbers
                words_only = []
                for line in content.strip().split('\n'):
                    if line:
                        parts = line.split('.')
                        if len(parts) > 1:
                            words_only.append(parts[1].strip())
                
                # Write one word per line
                file.write('\n'.join(words_only))
                
            self.update_status(f"Saved pseudowords to {file_path}")
            
        except Exception as e:
            self.update_status(f"Error saving file: {str(e)}")

# Create and run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = PseudowordGeneratorApp(root)
    root.mainloop()
